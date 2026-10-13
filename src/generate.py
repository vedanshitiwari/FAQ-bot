"""Phase 6 generation: Groq answer grounded only on retrieved chunks."""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SRC = Path(__file__).resolve().parent
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

_SCHEME_ALIASES: list[tuple[str, str]] = [
    ("balanced advantage", "HDFC Balanced Advantage Fund Direct Growth"),
    ("hybrid", "HDFC Balanced Advantage Fund Direct Growth"),
    ("small cap", "HDFC Small Cap Fund Direct Growth"),
    ("large cap", "HDFC Large Cap Fund Direct Growth"),
    ("flexi", "HDFC Flexi Cap Fund Direct Growth"),
    ("equity fund", "HDFC Flexi Cap Fund Direct Growth"),
    ("elss", "HDFC ELSS Tax Saver Direct Plan Growth"),
    ("tax saver", "HDFC ELSS Tax Saver Direct Plan Growth"),
]

DEFAULT_MODEL = "llama-3.1-8b-instant"
DEFAULT_K = 4


def load_config() -> dict[str, str]:
    from dotenv import load_dotenv

    load_dotenv(ROOT / ".env", override=False)
    api_key = (os.getenv("GROQ_API_KEY") or "").strip()
    model = (os.getenv("GROQ_MODEL") or "").strip() or DEFAULT_MODEL
    if not api_key:
        raise RuntimeError("GROQ_API_KEY is missing or empty in .env")
    return {"api_key": api_key, "model": model}


def bind_citation(question: str, hits: list[dict[str, Any]]) -> dict[str, Any]:
    """Bind one citation from retrieved chunk metadata."""
    if not hits:
        raise ValueError("cannot bind a citation without retrieved chunks")

    target_scheme = None
    lowered = question.lower()
    for alias, scheme_name in _SCHEME_ALIASES:
        if alias in lowered:
            target_scheme = scheme_name
            break

    selected = hits[0]
    if target_scheme is not None:
        for hit in hits:
            if (hit.get("metadata") or {}).get("scheme_name") == target_scheme:
                selected = hit
                break

    metadata = selected.get("metadata") or {}
    return {
        "citation_url": metadata.get("source_url"),
        "scheme_name": metadata.get("scheme_name"),
        "ingest_ts": metadata.get("ingest_ts"),
        "section_title": metadata.get("section_title"),
    }


def _truncate_to_sentences(text: str, max_sentences: int = 3) -> str:
    text = (text or "").strip()
    if not text:
        return text
    parts = re.split(r"(?<=[.!?])\s+", text)
    parts = [p.strip() for p in parts if p.strip()]
    if len(parts) <= max_sentences:
        return " ".join(parts)
    return " ".join(parts[:max_sentences])


def _build_context(hits: list[dict[str, Any]]) -> str:
    blocks = []
    for i, hit in enumerate(hits, start=1):
        metadata = hit.get("metadata") or {}
        blocks.append(
            f"[{i}] scheme_name: {metadata.get('scheme_name')}\n"
            f"source_url: {metadata.get('source_url')}\n"
            f"section_title: {metadata.get('section_title')}\n"
            f"text: {hit.get('text', '')}"
        )
    return "\n\n".join(blocks)


def generate_answer(
    question: str,
    hits: list[dict[str, Any]],
    config: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Generate a grounded answer and bind one citation from metadata."""
    if not hits:
        raise ValueError("retrieved context is required for generation")

    cfg = config or load_config()
    citation = bind_citation(question, hits)

    system_prompt = (
        "You are a factual FAQ assistant for five HDFC mutual fund schemes. "
        "Answer only from the provided retrieved context. Do not use outside "
        "knowledge. Do not give investment advice and do not compute or compare "
        "returns. Answer in at most 3 short sentences. Name the scheme when "
        "relevant. If a requested fact is not in the context, say that you do "
        "not have that fact in the sources. Do not include URLs; the citation "
        "is provided separately."
    )
    user_prompt = (
        f"Question: {question.strip()}\n\n"
        f"Retrieved context (numbered chunks):\n\n{_build_context(hits)}\n\n"
        "Answer with at most 3 sentences using only the facts above."
    )

    from groq import Groq

    client = Groq(api_key=cfg["api_key"])
    response = client.chat.completions.create(
        model=cfg["model"],
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.1,
        max_tokens=220,
    )

    content = ""
    if response.choices:
        content = response.choices[0].message.content or ""
    answer = _truncate_to_sentences(content.strip(), 3)
    if not answer:
        answer = "I could not generate an answer from the retrieved context."

    return {
        "answer": answer,
        "citation_url": citation.get("citation_url"),
        "scheme_name": citation.get("scheme_name"),
        "ingest_ts": citation.get("ingest_ts"),
        "model": cfg["model"],
    }


def main() -> int:
    # Tiny config smoke: proves import and env loading without calling Groq.
    try:
        cfg = load_config()
    except RuntimeError as exc:
        print(f"Config error: {exc}", file=sys.stderr)
        return 1
    print(f"Generation module ready. Configured model: {cfg['model']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
