"""Phase 1 loader: HTTP GET public Groww pages, extract text, save to data/raw/.

No chunking, embeddings, Chroma, Groq, or UI.
"""

from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw"
SOURCES = [
    {
        "category": "large-cap",
        "scheme_name": "HDFC Large Cap Fund Direct Growth",
        "slug": "hdfc-large-cap-fund-direct-growth",
        "url": "https://groww.in/mutual-funds/hdfc-large-cap-fund-direct-growth",
    },
    {
        "category": "flexi-cap",
        "scheme_name": "HDFC Flexi Cap Fund Direct Growth",
        "slug": "hdfc-equity-fund-direct-growth",
        "url": "https://groww.in/mutual-funds/hdfc-equity-fund-direct-growth",
    },
    {
        "category": "elss",
        "scheme_name": "HDFC ELSS Tax Saver Direct Plan Growth",
        "slug": "hdfc-elss-tax-saver-fund-direct-plan-growth",
        "url": "https://groww.in/mutual-funds/hdfc-elss-tax-saver-fund-direct-plan-growth",
    },
    {
        "category": "small-cap",
        "scheme_name": "HDFC Small Cap Fund Direct Growth",
        "slug": "hdfc-small-cap-fund-direct-growth",
        "url": "https://groww.in/mutual-funds/hdfc-small-cap-fund-direct-growth",
    },
    {
        "category": "hybrid",
        "scheme_name": "HDFC Balanced Advantage Fund Direct Growth",
        "slug": "hdfc-balanced-advantage-fund-direct-growth",
        "url": "https://groww.in/mutual-funds/hdfc-balanced-advantage-fund-direct-growth",
    },
]

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-IN,en;q=0.9",
}

NAV_NOISE = {
    "nav",
    "header",
    "footer",
    "aside",
    "form",
    "button",
    "svg",
    "noscript",
    "script",
    "style",
    "iframe",
}


def flatten_json(obj, prefix=""):
    """Yield human-readable key: value lines from nested JSON."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            key = f"{prefix}.{k}" if prefix else str(k)
            yield from flatten_json(v, key)
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from flatten_json(v, f"{prefix}[{i}]")
    elif obj is None:
        return
    else:
        text = str(obj).strip()
        if text:
            yield f"{prefix}: {text}"


def extract_next_data(html: str) -> str:
    soup = BeautifulSoup(html, "lxml")
    tag = soup.find("script", id="__NEXT_DATA__")
    if not tag or not tag.string:
        return ""
    try:
        data = json.loads(tag.string)
    except json.JSONDecodeError:
        return ""
    lines = list(flatten_json(data))
    return "\n".join(lines)


def extract_visible_html_text(html: str) -> str:
    soup = BeautifulSoup(html, "lxml")
    for tag in soup(NAV_NOISE):
        tag.decompose()
    text = soup.get_text(separator="\n")
    lines = [re.sub(r"\s+", " ", line).strip() for line in text.splitlines()]
    lines = [line for line in lines if line]
    return "\n".join(lines)


def trim_scheme_chrome(text: str) -> str:
    """Keep scheme body; drop mega-menu after the <title> line and site footer."""
    lines = text.splitlines()
    title_i = next(
        (i for i, line in enumerate(lines) if " - NAV, Mutual Fund Performance" in line),
        0,
    )
    nav_end = next(
        (i for i, line in enumerate(lines) if line.startswith("NAV:")),
        title_i,
    )
    # Keep the scheme title, skip product-menu lines between title and NAV.
    body_start = nav_end
    end = len(lines)
    for i, line in enumerate(lines[body_start:], start=body_start):
        if line.strip() in {"Download the App", "GROWW"} and i > body_start + 20:
            end = i
            break
    kept = [lines[title_i]] + lines[body_start:end]
    trimmed = "\n".join(kept).strip()
    return trimmed if trimmed else text


def extract_page_text(html: str) -> tuple[str, str]:
    """Return (text, method). Prefer visible HTML; fall back to __NEXT_DATA__."""
    visible = trim_scheme_chrome(extract_visible_html_text(html))
    next_data = extract_next_data(html)

    visible_len = len(visible)
    next_len = len(next_data)

    # Groww is often a JS app: visible HTML can be a thin shell.
    if visible_len >= 1500 and _looks_like_scheme_page(visible):
        return visible, "visible_html"
    if next_len > visible_len:
        return next_data, "next_data_json"
    if visible:
        return visible, "visible_html"
    return "", "empty"


def _looks_like_scheme_page(text: str) -> bool:
    lower = text.lower()
    hits = sum(
        1
        for needle in (
            "expense ratio",
            "exit load",
            "sip",
            "riskometer",
            "benchmark",
            "nav",
            "aum",
        )
        if needle in lower
    )
    return hits >= 2


def fetch(url: str) -> str:
    resp = requests.get(url, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    return resp.text


def write_raw(scheme: dict, html: str, text: str, method: str, ingest_ts: str) -> Path:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    (RAW_DIR / f"{scheme['slug']}.html").write_text(html, encoding="utf-8")
    header = [
        f"scheme_name: {scheme['scheme_name']}",
        f"category: {scheme['category']}",
        f"source_url: {scheme['url']}",
        f"ingest_ts: {ingest_ts}",
        f"extract_method: {method}",
        f"char_count: {len(text)}",
        "",
        "-----",
        "",
        text if text else "[EMPTY] Fetch succeeded but no extractable text.",
        "",
    ]
    out = RAW_DIR / f"{scheme['slug']}.txt"
    out.write_text("\n".join(header), encoding="utf-8")
    return out


def main() -> int:
    ingest_ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    failures: list[str] = []
    print(f"ingest_ts={ingest_ts}")
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    for scheme in SOURCES:
        url = scheme["url"]
        print(f"GET {url}")
        try:
            html = fetch(url)
        except requests.RequestException as exc:
            msg = f"FAIL {scheme['slug']}: {url} ({exc})"
            print(msg, file=sys.stderr)
            failures.append(msg)
            continue
        text, method = extract_page_text(html)
        path = write_raw(scheme, html, text, method, ingest_ts)
        print(f"  saved {path.name} method={method} chars={len(text)}")

    if failures:
        print("\nFetch failures:", file=sys.stderr)
        for line in failures:
            print(f"  {line}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
