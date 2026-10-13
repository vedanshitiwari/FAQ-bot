"""Phase 4 retrieval: embed question with MiniLM, query persisted Chroma top-k.

No Groq, no UI, no ingest on import or startup. Run as CLI for a smoke test.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

SRC = Path(__file__).resolve().parent
ROOT = SRC.parent
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
CHROMA_DIR = ROOT / "data" / "chroma"
COLLECTION_NAME = "hdfc_mf_faq"
DEFAULT_K = 4
MIN_K = 3
MAX_K = 5
DEFAULT_QUESTION = "What is the expense ratio of HDFC Large Cap Fund Direct Growth?"


def _validate_k(k: int) -> int:
    if not isinstance(k, int):
        try:
            k = int(k)
        except (TypeError, ValueError) as exc:
            raise ValueError("k must be an integer between 3 and 5") from exc
    if k < MIN_K or k > MAX_K:
        raise ValueError(f"k must be between {MIN_K} and {MAX_K}; got {k}")
    return k


_model_cache: Any = None


def _get_model() -> Any:
    global _model_cache
    if _model_cache is None:
        from sentence_transformers import SentenceTransformer

        _model_cache = SentenceTransformer(MODEL_NAME)
    return _model_cache


def retrieve(
    question: str,
    k: int = DEFAULT_K,
    where: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Return top-k chunks as {"text", "metadata", "distance"}.

    ``where`` is an optional Chroma metadata filter, for example
    ``{"scheme_name": "HDFC ELSS Tax Saver Direct Plan Growth"}``.
    """
    if not isinstance(question, str) or not question.strip():
        raise ValueError("question must be a non-empty string")

    k = _validate_k(k)

    if not CHROMA_DIR.exists():
        raise RuntimeError(
            "Chroma store not found at data/chroma/. "
            "Run `python src/ingest.py` first, then retry."
        )

    import chromadb

    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    try:
        collection = client.get_collection(COLLECTION_NAME)
    except Exception as exc:
        raise RuntimeError(
            "Chroma collection 'hdfc_mf_faq' is unavailable. "
            "Run `python src/ingest.py` first, then retry."
        ) from exc

    if collection.count() == 0:
        raise RuntimeError(
            "Chroma collection 'hdfc_mf_faq' is empty. "
            "Run `python src/ingest.py` first, then retry."
        )

    model = _get_model()
    query_vector = model.encode(
        [question.strip()],
        normalize_embeddings=True,
        show_progress_bar=False,
    ).tolist()

    query_kwargs = {
        "query_embeddings": query_vector,
        "n_results": k,
        "include": ["documents", "metadatas", "distances"],
    }
    if where:
        query_kwargs["where"] = where
    result = collection.query(**query_kwargs)

    documents = (result.get("documents") or [[]])[0]
    metadatas = (result.get("metadatas") or [[]])[0]
    distances = (result.get("distances") or [[]])[0]

    hits: list[dict[str, Any]] = []
    for text, metadata, distance in zip(documents, metadatas, distances):
        hits.append(
            {
                "text": text,
                "metadata": metadata or {},
                "distance": float(distance),
            }
        )
    return hits


def _format_hit(index: int, hit: dict[str, Any]) -> str:
    metadata = hit["metadata"]
    lines = [
        f"[{index}] distance={hit['distance']:.4f}",
        f"    scheme_name: {metadata.get('scheme_name')}",
        f"    source_url: {metadata.get('source_url')}",
        f"    section_title: {metadata.get('section_title')}",
        f"    ingest_ts: {metadata.get('ingest_ts')}",
        "    text:",
    ]
    for body_line in str(hit["text"]).splitlines():
        lines.append(f"      {body_line}")
    return "\n".join(lines)


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass
    parser = argparse.ArgumentParser(
        description="Retrieve top chunks from the HDFC Groww FAQ Chroma store."
    )
    parser.add_argument("question", nargs="?", default=DEFAULT_QUESTION)
    parser.add_argument("k", nargs="?", type=int, default=DEFAULT_K)
    args = parser.parse_args()

    try:
        hits = retrieve(args.question, args.k)
    except (RuntimeError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    print(f'Question: {args.question}')
    print(f"Top {len(hits)} chunks (k={args.k}):")
    for i, hit in enumerate(hits, start=1):
        print(_format_hit(i, hit))
        print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())