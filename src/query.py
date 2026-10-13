"""Phase 6 query pipeline: guards -> retrieve -> generate."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

SRC = Path(__file__).resolve().parent
ROOT = SRC.parent
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

DEFAULT_QUESTION = "What is the expense ratio of HDFC Large Cap Fund Direct Growth?"
DEFAULT_K = 4


def _print_refusal(result) -> int:
    print("Refused:", result.message)
    if result.citation_url:
        print("Citation:", result.citation_url)
    return 0


def run(question: str, k: int = DEFAULT_K) -> int:
    from guards import guard
    from retrieve import retrieve

    decision = guard(question)
    if decision.action != "allow":
        return _print_refusal(decision)

    try:
        hits = retrieve(question, k)
    except (RuntimeError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    from generate import generate_answer

    try:
        result = generate_answer(question, hits)
    except Exception as exc:
        print("Generation unavailable; no facts were guessed.", file=sys.stderr)
        print(f"Groq error: {exc}", file=sys.stderr)
        print(f"Retrieval did run ({len(hits)} chunks). Top sources:")
        for hit in hits:
            metadata = hit.get("metadata") or {}
            print(f"  - {metadata.get('scheme_name')}: {metadata.get('source_url')}")
        return 1

    print("Answer:", result["answer"])
    print("Citation:", result["citation_url"])
    print("Last updated from sources:", result["ingest_ts"])
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Ask a factual question about the five HDFC Groww schemes."
    )
    parser.add_argument("question", nargs="?", default=DEFAULT_QUESTION)
    parser.add_argument("k", nargs="?", type=int, default=DEFAULT_K)
    args = parser.parse_args()

    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

    return run(args.question, args.k)


if __name__ == "__main__":
    raise SystemExit(main())
