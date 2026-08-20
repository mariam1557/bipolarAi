"""
يقرا كل الـ chunks بتاعة NICE CG185 من data/all_chunks.json (اللي عملها src/ingest.py)
ويحطهم في نفس Chroma بتاعة الباك إند، بنفس طريقة seed.py.

Run with: python -m app.seed_data.seed_nice
"""
import json
from pathlib import Path

from app.database import SessionLocal, Base, engine
from app import models
from app.services import vector_store

DOCUMENT_NAME = "NICE CG185 Bipolar Disorder"


def find_chunks_file() -> Path:
    """يدور على data/all_chunks.json صاعد من مكان الملف ده لحد ما يلاقيه."""
    here = Path(__file__).resolve()
    for parent in here.parents:
        candidate = parent / "data" / "all_chunks.json"
        if candidate.exists():
            return candidate
    raise FileNotFoundError(
        "مش لاقي data/all_chunks.json في أي مكان فوق هذا الملف. "
        "اتأكدي إنك عملتي python src/ingest.py الأول."
    )


def run():
    chunks_path = find_chunks_file()
    print(f"Loading chunks from: {chunks_path}")

    with open(chunks_path, "r", encoding="utf-8") as f:
        all_chunks = json.load(f)

    print(f"Found {len(all_chunks)} chunks total.")

    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    # هنجمع عدد الـ chunks لكل فصل عشان نسجل صف واحد لكل فصل في ClinicalDocument
    chapter_counts: dict[str, int] = {}

    try:
        for chunk in all_chunks:
            title = f"{DOCUMENT_NAME} — {chunk['chapter_title']}"
            category = chunk.get("section_title") or chunk["chapter_title"]
            page = str(chunk.get("page_number", ""))
            doc_id = chunk["chunk_id"]  # فريد لكل chunk أصلاً من ingest.py

            vector_store.add_chunks(
                chunks=[chunk["text"]],
                title=title,
                category=category,
                page=page,
                doc_id=doc_id,
            )

            chapter_counts[title] = chapter_counts.get(title, 0) + 1

        for title, count in chapter_counts.items():
            db.add(models.ClinicalDocument(
                title=title,
                category=DOCUMENT_NAME,
                page="",
                chunk_count=count,
            ))
        db.commit()

        print(f"Seeded {len(all_chunks)} chunks across {len(chapter_counts)} chapters into Chroma.")
        print(f"Chroma collection now has {vector_store.collection_count()} total chunks.")
    finally:
        db.close()


if __name__ == "__main__":
    run()