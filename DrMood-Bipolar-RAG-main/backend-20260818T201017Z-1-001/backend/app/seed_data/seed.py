"""
Run with: python -m app.seed_data.seed
Loads a couple of sample "approved clinical source" excerpts into the vector
store + database, purely so the app is demoable out of the box. Replace with
your own vetted clinical guideline content via the /api/documents endpoints
before using this with real patients.
"""
from app.database import SessionLocal, Base, engine
from app import models
from app.services import vector_store

SAMPLE_SOURCES = [
    {
        "title": "Bipolar Disorder Clinical Guideline",
        "category": "Mania",
        "page": "12",
        "text": (
            "A manic episode is a distinct period of abnormally elevated, expansive, or "
            "irritable mood and increased activity or energy, lasting at least one week and "
            "present most of the day, nearly every day. During this period, three or more of "
            "the following are present to a significant degree: inflated self-esteem or "
            "grandiosity, decreased need for sleep, being more talkative than usual or "
            "pressure to keep talking, flight of ideas or subjective racing thoughts, "
            "distractibility, increase in goal-directed activity or psychomotor agitation, "
            "and excessive involvement in activities with a high potential for painful "
            "consequences. The episode causes marked impairment in social or occupational "
            "functioning, or requires hospitalization, or includes psychotic features."
        ),
    },
    {
        "title": "Approved Mental Health Reference",
        "category": "Bipolar I",
        "page": "8",
        "text": (
            "Bipolar I disorder is defined by the occurrence of at least one manic episode. "
            "The manic episode may be preceded by or followed by hypomanic or major "
            "depressive episodes. Mood, energy, and activity levels shift together, and "
            "changes in functioning are usually noticeable to family, friends, or colleagues, "
            "even when the person experiencing the episode does not feel that anything is "
            "wrong. Accurate diagnosis relies on a full clinical history rather than a single "
            "conversation, since elevated mood can also occur in other conditions."
        ),
    },
    {
        "title": "Bipolar Disorder Clinical Guideline",
        "category": "Hypomania",
        "page": "15",
        "text": (
            "Hypomania shares the same core symptoms as mania — elevated or irritable mood "
            "with increased energy — but is less severe. A hypomanic episode lasts at least "
            "four consecutive days, does not cause marked impairment in social or "
            "occupational functioning, does not require hospitalization, and does not include "
            "psychotic features. Because functioning is preserved, hypomania is often not "
            "recognized as a problem by the person experiencing it."
        ),
    },
    {
        "title": "Bipolar Disorder Clinical Guideline",
        "category": "Treatment",
        "page": "34",
        "text": (
            "Management of bipolar disorder is individualized by a treating clinician and "
            "typically combines pharmacological treatment with psychosocial support such as "
            "psychoeducation, structured routine, and therapy. Treatment plans, medication "
            "choice, and dosing are determined case-by-case based on episode type, history, "
            "and response, and require ongoing monitoring by a qualified prescriber."
        ),
    },
]


def run():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        for src in SAMPLE_SOURCES:
            chunk_count = vector_store.add_chunks(
                chunks=[src["text"]],
                title=src["title"],
                category=src["category"],
                page=src["page"],
            )
            db.add(models.ClinicalDocument(
                title=src["title"],
                category=src["category"],
                page=src["page"],
                chunk_count=chunk_count,
            ))
        db.commit()
        print(f"Seeded {len(SAMPLE_SOURCES)} sample clinical source excerpts.")
    finally:
        db.close()


if __name__ == "__main__":
    run()
