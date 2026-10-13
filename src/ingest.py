"""Ingest CLI — Phase 3: Load (existing raw files) → Chunk → Embed → Store.

Explicit CLI only. Importing this module does NOT embed or touch Chroma.
"""

from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

SRC = Path(__file__).resolve().parent
ROOT = SRC.parent
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from chunk import chunk_raw_dir, format_chunks_file  # noqa: E402

RAW_DIR = ROOT / "data" / "raw"
OUT_PATH = ROOT / "data" / "chunks.txt"
CHROMA_DIR = ROOT / "data" / "chroma"
COLLECTION_NAME = "hdfc_mf_faq"
MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"


def _fail_no_raw() -> None:
    raise SystemExit(
        "No extracted raw .txt files found in data/raw/. "
        "Run `python src/load_pages.py` first, then re-run ingest."
    )


def main() -> int:
    # --- Load + Chunk (reuses data/raw produced by load_pages.py) ---
    if not RAW_DIR.is_dir() or not any(RAW_DIR.glob("*.txt")):
        _fail_no_raw()

    chunks = chunk_raw_dir(RAW_DIR)
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(format_chunks_file(chunks), encoding="utf-8")

    by_scheme = Counter(c.scheme_name for c in chunks)
    by_section = Counter(c.section_title for c in chunks)
    print(f"Wrote {len(chunks)} chunks to {OUT_PATH}")
    print("By scheme:")
    for name, n in by_scheme.items():
        print(f"  {n:4d}  {name}")
    print("By section:")
    for title, n in by_section.most_common():
        print(f"  {n:4d}  {title}")

    # --- Embed (chunk text only) ---
    print(f"\nEmbedding {len(chunks)} chunks with {MODEL_NAME} ...")
    from sentence_transformers import SentenceTransformer

    model = SentenceTransformer(MODEL_NAME)
    texts = [c.body for c in chunks]
    embeddings = model.encode(
        texts,
        normalize_embeddings=True,
        show_progress_bar=False,
    ).tolist()
    print(f"  produced {len(embeddings)} x {len(embeddings[0])} vectors")

    # --- Store (replace collection on re-ingest) ---
    import chromadb

    CHROMA_DIR.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(CHROMA_DIR))

    try:
        client.delete_collection(COLLECTION_NAME)
        print(f"  replaced existing collection '{COLLECTION_NAME}'")
    except Exception:
        print(f"  created new collection '{COLLECTION_NAME}'")

    collection = client.create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )

    BATCH = 100
    total = 0
    for offset in range(0, len(chunks), BATCH):
        sl = slice(offset, offset + BATCH)
        batch_chunks = chunks[sl]
        collection.add(
            ids=[f"chunk-{offset + i:04d}" for i in range(len(batch_chunks))],
            documents=[c.body for c in batch_chunks],
            embeddings=embeddings[sl],
            metadatas=[
                {
                    "source_url": c.source_url,
                    "scheme_name": c.scheme_name,
                    "category": c.category,
                    "section_title": c.section_title,
                    "ingest_ts": c.ingest_ts,
                }
                for c in batch_chunks
            ],
        )
        total += len(batch_chunks)

    print(f"\nStored {collection.count()} records in '{COLLECTION_NAME}'")
    print(f"  (added {total}; chunk count was {len(chunks)})")
    print(f"  persist dir: {CHROMA_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())