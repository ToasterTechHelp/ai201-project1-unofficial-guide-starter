"""Milestone 4 (part 1) — Embed chunks and load them into ChromaDB.

Reads chunks.json (from ingest.py), embeds each chunk with the local
all-MiniLM-L6-v2 model, and stores them in a persistent ChromaDB collection
with source metadata for attribution. The collection uses cosine distance so
retrieval scores fall in a familiar 0 (identical) .. 2 (opposite) range.

Run once to (re)build the store:  python embed.py
"""

import json
from pathlib import Path

import chromadb
from sentence_transformers import SentenceTransformer

CHUNKS_FILE = Path("chunks.json")
CHROMA_DIR = "chroma_db"
COLLECTION_NAME = "tax_forms"
EMBED_MODEL = "all-MiniLM-L6-v2"


def build() -> None:
    chunks = json.loads(CHUNKS_FILE.read_text(encoding="utf-8"))
    if not chunks:
        raise SystemExit("chunks.json is empty — run ingest.py first.")

    print(f"Loading embedding model: {EMBED_MODEL} ...")
    model = SentenceTransformer(EMBED_MODEL)

    print(f"Embedding {len(chunks)} chunks ...")
    embeddings = model.encode(
        [c["text"] for c in chunks],
        show_progress_bar=True,
        normalize_embeddings=True,
    ).tolist()

    client = chromadb.PersistentClient(path=CHROMA_DIR)
    # start clean so re-runs don't duplicate or stale-cache chunks
    if COLLECTION_NAME in [c.name for c in client.list_collections()]:
        client.delete_collection(COLLECTION_NAME)
    collection = client.create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )

    collection.add(
        ids=[c["id"] for c in chunks],
        documents=[c["text"] for c in chunks],
        embeddings=embeddings,
        metadatas=[{"source": c["source"], "chunk_index": c["chunk_index"]} for c in chunks],
    )

    print(f"Stored {collection.count()} chunks in ChromaDB collection '{COLLECTION_NAME}' ({CHROMA_DIR}/).")


if __name__ == "__main__":
    build()
