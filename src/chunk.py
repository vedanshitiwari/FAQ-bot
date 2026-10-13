"""Phase 2 chunker: heading-first, then 800/150 character windows.

Reads data/raw/*.txt only. No embeddings, Chroma, Groq, or UI.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

CHUNK_SIZE = 800
CHUNK_OVERLAP = 150

# (section_title, line matcher). First match in document order wins.
# snapshot is everything before the first of these.
SECTION_ANCHORS: list[tuple[str, str]] = [
    ("noise", "Return calculator"),
    ("holdings", "Holdings ("),
    ("understand_terms", "Understand terms"),
    ("exit_load", "Exit Load"),
    ("noise", "Compare similar funds"),
    ("fund_management", "Fund management"),
    ("about", "About"),
    ("investment_objective", "Investment Objective"),
    ("benchmark", "Fund benchmark"),
]

# After benchmark, leftover AMC/RTA/footer is noise.
KEEP_WHOLE_IF_SHORT = {"snapshot", "about"}


@dataclass
class RawPage:
    scheme_name: str
    category: str
    source_url: str
    ingest_ts: str
    body: str
    path: Path


@dataclass
class Chunk:
    scheme_name: str
    category: str
    source_url: str
    section_title: str
    ingest_ts: str
    body: str


def parse_raw_file(path: Path) -> RawPage:
    text = path.read_text(encoding="utf-8")
    if "-----" not in text:
        raise ValueError(f"Missing header separator in {path}")
    header, body = text.split("-----", 1)
    meta: dict[str, str] = {}
    for line in header.splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            meta[key.strip()] = value.strip()
    required = ("scheme_name", "category", "source_url", "ingest_ts")
    missing = [k for k in required if k not in meta]
    if missing:
        raise ValueError(f"{path} missing {missing}")
    return RawPage(
        scheme_name=meta["scheme_name"],
        category=meta["category"],
        source_url=meta["source_url"],
        ingest_ts=meta["ingest_ts"],
        body=body.strip(),
        path=path,
    )


def _anchor_kind(line: str) -> str | None:
    stripped = line.strip()
    for title, prefix in SECTION_ANCHORS:
        if prefix.endswith("("):
            if stripped.startswith(prefix):
                return title
        elif stripped == prefix:
            return title
    return None


def split_sections(body: str) -> list[tuple[str, str]]:
    """Split body into (section_title, text) in document order."""
    lines = body.splitlines()
    sections: list[tuple[str, list[str]]] = [("snapshot", [])]
    for line in lines:
        kind = _anchor_kind(line)
        if kind is not None:
            sections.append((kind, [line]))
        else:
            sections[-1][1].append(line)
    out: list[tuple[str, str]] = []
    for title, slines in sections:
        text = "\n".join(slines).strip()
        if not text:
            continue
        if title == "benchmark":
            text, leftover = _split_benchmark_footer(text)
            if text:
                out.append((title, text))
            if leftover:
                out.append(("noise", leftover))
        else:
            out.append((title, text))
    return out


def _split_benchmark_footer(text: str) -> tuple[str, str]:
    """Keep Fund benchmark + index name; leftover fund-house/RTA is noise."""
    lines = text.splitlines()
    cut = None
    for i, line in enumerate(lines):
        if line.strip() in {"Fund house", "Scheme Information Document(SID)"}:
            cut = i
            break
    if cut is None:
        return text.strip(), ""
    keep = "\n".join(lines[:cut]).strip()
    rest = "\n".join(lines[cut:]).strip()
    return keep, rest


def window_split(text: str, size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    text = text.strip()
    if not text:
        return []
    if len(text) <= size:
        return [text]
    chunks: list[str] = []
    start = 0
    n = len(text)
    while start < n:
        end = min(start + size, n)
        if end < n:
            nl = text.rfind("\n", start, end)
            if nl >= start + (size // 2):
                end = nl
        piece = text[start:end].strip()
        if piece:
            chunks.append(piece)
        if end >= n:
            break
        next_start = end - overlap
        if next_start <= start:
            next_start = end
        start = next_start
    return chunks


def chunk_page(page: RawPage) -> list[Chunk]:
    chunks: list[Chunk] = []
    for title, section_text in split_sections(page.body):
        if title in KEEP_WHOLE_IF_SHORT and len(section_text) <= CHUNK_SIZE:
            parts = [section_text]
        else:
            parts = window_split(section_text)
        for part in parts:
            chunks.append(
                Chunk(
                    scheme_name=page.scheme_name,
                    category=page.category,
                    source_url=page.source_url,
                    section_title=title,
                    ingest_ts=page.ingest_ts,
                    body=part,
                )
            )
    return chunks


def format_chunks_file(chunks: list[Chunk]) -> str:
    blocks = [
        "HDFC Groww FAQ chunks (Phase 2)",
        f"chunk_size={CHUNK_SIZE} overlap={CHUNK_OVERLAP}",
        f"total_chunks={len(chunks)}",
        "",
    ]
    for i, chunk in enumerate(chunks, start=1):
        blocks.append("=" * 80)
        blocks.append(f"chunk_id: {i:04d}")
        blocks.append(f"scheme_name: {chunk.scheme_name}")
        blocks.append(f"category: {chunk.category}")
        blocks.append(f"source_url: {chunk.source_url}")
        blocks.append(f"section_title: {chunk.section_title}")
        blocks.append(f"ingest_ts: {chunk.ingest_ts}")
        blocks.append(f"char_count: {len(chunk.body)}")
        blocks.append("-" * 80)
        blocks.append(chunk.body)
        blocks.append("")
    return "\n".join(blocks).rstrip() + "\n"


def chunk_raw_dir(raw_dir: Path) -> list[Chunk]:
    paths = sorted(p for p in raw_dir.glob("*.txt") if p.is_file())
    if not paths:
        raise FileNotFoundError(f"No .txt files in {raw_dir}")
    chunks: list[Chunk] = []
    for path in paths:
        chunks.extend(chunk_page(parse_raw_file(path)))
    return chunks
