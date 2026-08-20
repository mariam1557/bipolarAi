"""
Thin wrapper around ChromaDB (local, persistent, no external service required).
Embeddings are generated locally with sentence-transformers, so no API key
is needed just to index or search the clinical source library.
"""
import uuid
from pathlib import Path
from typing import Optional

import chromadb
from chromadb.utils import embedding_functions

from app.config import settings

_persist_dir = Path(settings.chroma_persist_dir)
if not _persist_dir.is_absolute():
    _persist_dir = Path(__file__).resolve().parents[2] / _persist_dir

_client = chromadb.PersistentClient(path=str(_persist_dir))
_embedder = embedding_functions.SentenceTransformerEmbeddingFunction(
    model_name=settings.embedding_model
)

_collection = _client.get_or_create_collection(
    name=settings.chroma_collection,
    embedding_function=_embedder,
    metadata={"hnsw:space": "cosine"},
)


def add_chunks(
    chunks: list[str],
    title: str,
    category: str = "",
    page: str = "",
    doc_id: Optional[str] = None,
) -> int:
    """Add a list of text chunks belonging to one source document. Returns chunk count."""
    doc_id = doc_id or uuid.uuid4().hex
    ids = [f"{doc_id}::{i}" for i in range(len(chunks))]
    metadatas = [
        {"title": title, "category": category, "page": page, "doc_id": doc_id}
        for _ in chunks
    ]
    _collection.add(ids=ids, documents=chunks, metadatas=metadatas)
    return len(chunks)


def query(text: str, top_k: int = 4) -> list[dict]:
    """Return the top_k most relevant chunks with a 0-1 similarity score (higher = better)."""
    if _collection.count() == 0:
        return []

    results = _collection.query(
        query_texts=[text],
        n_results=min(top_k, _collection.count()),
    )

    out = []
    docs = results.get("documents", [[]])[0]
    metas = results.get("metadatas", [[]])[0]
    distances = results.get("distances", [[]])[0]

    for doc, meta, dist in zip(docs, metas, distances):
        # Chroma cosine "distance" is 1 - cosine_similarity; convert back to a 0-1 score.
        score = max(0.0, 1.0 - dist)
        out.append({
            "text": doc,
            "title": meta.get("title", "Unknown source"),
            "category": meta.get("category", ""),
            "page": meta.get("page", ""),
            "doc_id": meta.get("doc_id", ""),
            "score": round(score, 4),
        })
    return out


def collection_count() -> int:
    return _collection.count()