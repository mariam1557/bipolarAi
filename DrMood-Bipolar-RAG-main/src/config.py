"""Project configuration. Edit settings here rather than in multiple files."""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

ROOT_DIR = Path(__file__).resolve().parent.parent
PDF_DIR = ROOT_DIR / "data" / "pdfs"
MERGED_PDF_PATH = PDF_DIR / "ilovepdf_merged.pdf"
CHUNKS_PATH = ROOT_DIR / "data" / "all_chunks.json"
CHROMA_DIR = ROOT_DIR / "chroma_db"
EVAL_XLSX_PATH = ROOT_DIR / "eval" / "Day2_Evaluation_Test_Set_Bipolar.xlsx"

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.6-flash")

# The embedding model was chosen based on Day 2 experiments (gte-base performed best).
# Change this to any compatible sentence-transformers model if desired.
EMBEDDING_MODEL = "thenlper/gte-base"
COLLECTION_NAME = "bipolar_guideline"

# If the nearest result is farther than this threshold (ChromaDB returns "distance", not "similarity";
# smaller means more similar), the system refuses instead of fabricating an answer.
# Start with 0.8 and adjust after evaluating refusal performance (see evaluate.py).
REFUSAL_DISTANCE_THRESHOLD = 0.8

# ترتيب الفصول وعناوينها زي ما هي في NICE CG185. ingest.py بيكتشف بداية كل فصل
# تلقائيًا جوه ملف الـ PDF المدمج (مش محتاجة start_page يدوي ولا ملفات منفصلة).
CHAPTER_TITLES = {
    2: "Introduction to Bipolar Disorder",
    4: "Improving the Experience of Carers",
    5: "Case Identification and Assessment",
    6: "Pharmacological Interventions for Acute Episodes",
    7: "Interventions and Services for Long-term Management",
    8: "Psychological and Psychosocial Interventions",
    9: "Management of Physical Health",
    10: "Interventions for Children and Young People",
    11: "Summary of Recommendations",
}
CHAPTER_ORDER = [2, 4, 5, 6, 7, 8, 9, 10, 11]

DOCUMENT_NAME = "NICE CG185 Bipolar Disorder"
