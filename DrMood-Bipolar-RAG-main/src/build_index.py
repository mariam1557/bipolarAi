import json
import os

import chromadb
from sentence_transformers import SentenceTransformer

from config import CHUNKS_PATH, CHROMA_DIR, COLLECTION_NAME, EMBEDDING_MODEL


def main():
    if not CHUNKS_PATH.exists():
        raise SystemExit(f"Missing {CHUNKS_PATH} — run src/ingest.py first.")

    with open(CHUNKS_PATH, encoding="utf-8") as f:
        all_chunks = json.load(f)

    print(f"Loading embedding model: {EMBEDDING_MODEL} ...")
    model = SentenceTransformer(EMBEDDING_MODEL)

    all_texts = [c["text"] for c in all_chunks]
    print(f"Creating embeddings for {len(all_texts)} chunks ...")
    all_embeddings = model.encode(all_texts, show_progress_bar=True)

    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    try:
        client.delete_collection(name=COLLECTION_NAME)
    except Exception:
        pass
    collection = client.create_collection(name=COLLECTION_NAME, metadata={"hnsw:space": "cosine"})

    ids = [c["chunk_id"] for c in all_chunks]
    documents = [c["text"] for c in all_chunks]
    metadatas = [
        {
            "chapter_number": c["chapter_number"],
            "chapter_title": c["chapter_title"],
            "section_number": c["section_number"],
            "section_title": c["section_title"],
            "page_number": c["page_number"],
        }
        for c in all_chunks
    ]

    collection.add(ids=ids, documents=documents, metadatas=metadatas, embeddings=all_embeddings.tolist())
    print(f"Saved {collection.count()} chunks to ChromaDB ({CHROMA_DIR})")


if __name__ == "__main__":
    main()
