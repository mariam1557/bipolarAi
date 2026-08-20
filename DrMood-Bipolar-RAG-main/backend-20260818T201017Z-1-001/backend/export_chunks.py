import json
import chromadb

client = chromadb.PersistentClient(path="./chroma_store")
collection = client.get_collection("clinical_sources")

data = collection.get(include=["documents", "metadatas"])

chunks = [
    {"id": _id, "text": doc, "metadata": meta}
    for _id, doc, meta in zip(data["ids"], data["documents"], data["metadatas"])
]

with open("chunks_backup.json", "w", encoding="utf-8") as f:
    json.dump(chunks, f, ensure_ascii=False, indent=2)

print(f"Exported {len(chunks)} chunks to chunks_backup.json")