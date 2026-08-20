"""Split the merged NICE PDF (ilovepdf_merged.pdf) into text chunks by section number.

Automatically detects:
  - the real page number from the repeated header ("Bipolar disorder (update)  N")
  - the start of each chapter (by matching the next expected chapter in CHAPTER_ORDER)

No need for separate PDF files or manual page-number inputs.

Run: python src/ingest.py
"""
import json
import re

from config import MERGED_PDF_PATH, CHUNKS_PATH, CHAPTER_TITLES, CHAPTER_ORDER
from pypdf import PdfReader

PAGE_NUMBER_PATTERN = re.compile(r'Bipolar disorder \(update\)\s+(\d+)')
SECTION_PATTERN = re.compile(
    r'^(\d{1,2}(?:\.\d{1,2}){0,2})\s+([A-Z][A-Za-z ,\-]{3,80})\s*$',
    re.MULTILINE,
)


def clean_header(text: str) -> str:
    lines = text.split("\n")
    cleaned_lines = [line for line in lines if "Bipolar disorder (update)" not in line]
    return "\n".join(cleaned_lines).strip()


def extract_page_number(raw_text: str):
    m = PAGE_NUMBER_PATTERN.search(raw_text)
    return int(m.group(1)) if m else None


def is_chapter_start(raw_text: str, expected_chapter_num: int) -> bool:
    """Ensure the first thing after the header is the expected chapter number."""
    body = PAGE_NUMBER_PATTERN.sub("", raw_text, count=1).lstrip()
    return bool(re.match(rf'^{expected_chapter_num}\s+[A-Z]', body))


def validate_and_fix_section(section_num: str, chapter_num: int):
    """Validate and (if needed) fix a detected section number.

    Rules:
    1. If it starts with the chapter number -> valid
    2. If it starts with '1.1.' -> valid (NICE numbering)
    3. Try prefixing '1' for the missing leading '1' case (chapter 10 fix)
    4. Otherwise invalid
    """
    chapter_str = str(chapter_num)
    if section_num == chapter_str or section_num.startswith(chapter_str + "."):
        return True, section_num
    if section_num.startswith("1.1."):
        return True, section_num
    candidate = "1" + section_num
    if candidate == chapter_str or candidate.startswith(chapter_str + "."):
        return True, candidate
    return False, None


def load_pages_with_chapters(pdf_path):
    """بيرجع قايمة صفحات، كل صفحة فيها: page_number الحقيقي، chapter_number، chapter_title، النص المنضف."""
    reader = PdfReader(str(pdf_path))
    chapter_queue = list(CHAPTER_ORDER)
    current_chapter_num = None
    pages = []

    for page in reader.pages:
        raw_text = page.extract_text()

        if chapter_queue and is_chapter_start(raw_text, chapter_queue[0]):
            current_chapter_num = chapter_queue.pop(0)

        if current_chapter_num is None:
            continue  # صفحات غلاف/فهرس قبل أول فصل معروف — اتجاهلها

        page_number = extract_page_number(raw_text)
        pages.append({
            "page_number": page_number,
            "chapter_number": current_chapter_num,
            "chapter_title": CHAPTER_TITLES[current_chapter_num],
            "text": clean_header(raw_text),
        })

    return pages


def chunk_chapter(chapter_num, chapter_title, chapter_pages):
    chunks = []
    current_chunk_text = ""
    current_section_number = str(chapter_num)
    current_section_title = chapter_title
    current_start_page = chapter_pages[0]["page_number"]

    def save_chunk():
        if current_chunk_text.strip():
            chunks.append({
                "chunk_id": f"ch{chapter_num:02d}_{current_section_number}_{len(chunks) + 1:03d}",
                "chapter_number": chapter_num,
                "chapter_title": chapter_title,
                "section_number": current_section_number,
                "section_title": current_section_title,
                "page_number": current_start_page,
                "text": current_chunk_text.strip(),
            })

    for page in chapter_pages:
        page_num = page["page_number"]
        text = page["text"]
        found_sections = list(SECTION_PATTERN.finditer(text))
        last_end = 0
        for m in found_sections:
            is_valid, fixed_section_num = validate_and_fix_section(m.group(1), chapter_num)
            if not is_valid:
                continue
            before_text = text[last_end:m.start()]
            current_chunk_text += "\n" + before_text
            save_chunk()
            current_chunk_text = ""
            current_section_number = fixed_section_num
            current_section_title = m.group(2).strip()
            current_start_page = page_num
            last_end = m.start()
        current_chunk_text += "\n" + text[last_end:]
    save_chunk()

    # دمج الأقسام الفاضية (أقل من 20 كلمة) مع أول sub-section بتاعتها
    merged = []
    skip_merge = {}
    for i in range(len(chunks) - 1):
        parent, child = chunks[i], chunks[i + 1]
        if child["section_number"].startswith(parent["section_number"] + ".") and len(parent["text"].split()) < 20:
            skip_merge[i] = i + 1
    i = 0
    while i < len(chunks):
        if i in skip_merge:
            parent, child = chunks[i], chunks[i + 1]
            merged.append({**child, "page_number": parent["page_number"],
                           "text": parent["text"].strip() + "\n" + child["text"].strip()})
            i += 2
        else:
            merged.append(chunks[i])
            i += 1
    return merged


def main():
    if not MERGED_PDF_PATH.exists():
        raise SystemExit(
            f"Missing {MERGED_PDF_PATH}.\n"
            "Place ilovepdf_merged.pdf in data/pdfs/ before running this script."
        )

    pages = load_pages_with_chapters(MERGED_PDF_PATH)
    if not pages:
        raise SystemExit("No pages belonging to known chapters were found — check CHAPTER_ORDER in config.py.")

    all_chunks = []
    for chapter_num in CHAPTER_ORDER:
        chapter_pages = [p for p in pages if p["chapter_number"] == chapter_num]
        if not chapter_pages:
            print(f"⚠️  No pages found for chapter {chapter_num}.")
            continue
        chapter_chunks = chunk_chapter(chapter_num, CHAPTER_TITLES[chapter_num], chapter_pages)
        all_chunks.extend(chapter_chunks)
        print(f"Chapter {chapter_num}: {len(chapter_pages)} pages -> {len(chapter_chunks)} chunks")

    CHUNKS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(CHUNKS_PATH, "w", encoding="utf-8") as f:
        json.dump(all_chunks, f, ensure_ascii=False, indent=2)

    suspicious = [c for c in all_chunks if c["section_number"].startswith("0.")]
    print()
    print("Done! Total chunks:", len(all_chunks))
    print("Suspicious (possible malformed) sections:", len(suspicious))
    print(f"Saved to: {CHUNKS_PATH}")


if __name__ == "__main__":
    main()
