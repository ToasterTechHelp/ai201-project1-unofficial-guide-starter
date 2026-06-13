"""Milestone 4 (part 2) — Semantic retrieval over the ChromaDB store.

Loads the embedding model + persistent collection once, then exposes
retrieve(query, k=5) returning the top-k chunks with their source and cosine
distance. Run directly to test retrieval on the evaluation-plan questions.

Run:  python retrieve.py
"""

import chromadb
from sentence_transformers import SentenceTransformer

from embed import CHROMA_DIR, COLLECTION_NAME, EMBED_MODEL

TOP_K = 5  # see planning.md "Retrieval Approach"

_model = SentenceTransformer(EMBED_MODEL)
_collection = chromadb.PersistentClient(path=CHROMA_DIR).get_collection(COLLECTION_NAME)


def retrieve(query: str, k: int = TOP_K) -> list[dict]:
    """Return the top-k most semantically similar chunks to `query`."""
    q_emb = _model.encode([query], normalize_embeddings=True).tolist()
    res = _collection.query(query_embeddings=q_emb, n_results=k)
    return [
        {
            "text": doc,
            "source": meta["source"],
            "chunk_index": meta["chunk_index"],
            "distance": dist,
        }
        for doc, meta, dist in zip(
            res["documents"][0], res["metadatas"][0], res["distances"][0]
        )
    ]


# A subset of the planning.md evaluation questions, for the M4 retrieval check.
TEST_QUERIES = [
    "What is Schedule C (Form 1040) used for?",
    "What does an employer report on Form 941?",
    "What expenses does Form 8829 calculate?",
]


def _demo() -> None:
    for q in TEST_QUERIES:
        print(f"\n{'=' * 80}\nQUERY: {q}\n{'=' * 80}")
        for i, r in enumerate(retrieve(q), 1):
            preview = r["text"].replace("\n", " ")[:160]
            print(f"{i}. [{r['source']}#{r['chunk_index']}] distance={r['distance']:.3f}")
            print(f"   {preview}...")


if __name__ == "__main__":
    _demo()
