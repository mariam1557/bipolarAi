from app.config import settings
from app.services import vector_store, llm, drug_names
import re


SECTION_FROM_DOC_ID = re.compile(r"^ch\d+_([\d.]+)_")


def _section_number(doc_id: str) -> str:
    match = SECTION_FROM_DOC_ID.match(doc_id or "")
    return match.group(1) if match else ""

def retrieve_evidence(question: str) -> list[dict]:
    """Retrieve candidate chunks and mark which ones clear the relevance threshold."""
    search_query = question
    if any("\u0600" <= ch <= "\u06FF" for ch in question):
        search_query = llm.translate_to_english(question)
    raw = vector_store.query(search_query, top_k=settings.retrieval_top_k)
    shaped = []
    for rank, c in enumerate(raw, start=1):
        section_number = _section_number(c.get("doc_id", ""))
        category = c["category"]
        source_meta = " • ".join(
            part for part in [
                f"Section {section_number}" if section_number else "",
                category,
                f"p. {c['page']}" if c["page"] else "",
            ] if part
        )
        shaped.append({
            "source_title": c["title"],
            "source_meta": source_meta,
            "section_number": section_number,
            "snippet": _summarize(c["text"]),
            "full_text": c["text"],
            "score": c["score"],
            "used": c["score"] >= settings.retrieval_min_score,
            "rank": rank,
        })
    return shaped


def _summarize(text: str, max_chars: int = 160) -> str:
    text = " ".join(text.split())
    return text if len(text) <= max_chars else text[:max_chars].rsplit(" ", 1)[0] + "…"


def answer_question(role: str, question: str, history: list[dict]) -> tuple[str, list[dict]]:
    """
    Full RAG turn: retrieve ALL top_k approved chunks, generate a grounded answer
    that cites them by number, return (answer_text, evidence_list). `history` is
    prior turns as [{"role": "user"|"assistant", "content": "..."}].
    """
    evidence = retrieve_evidence(question)

    # لو مفيش ولا مصدر واحد وصل للعتبة، منبعتش أي حاجة ضعيفة/مش متعلقة للموديل خالص
    # ونرجع رفض واضح بدل ما نسيبه يحاول يخمن من سياق مش مضمون
    if not any(e["used"] for e in evidence):
        refusal = (
            "I couldn't find approved clinical source material that directly answers this "
            "question. Please rephrase, ask something more specific, or check with your care team."
        )
        return refusal, evidence

    if not settings.gemini_api_key:
        return (
            "I found approved clinical sources that may help answer this question, but "
            "answer generation is not configured yet. Add GEMINI_API_KEY to the backend "
            ".env file, then restart the server.",
            evidence,
        )

    # نبعت كل الـ top_k للـ LLM، مش بس اللي فوق العتبة، عشان يقدر يستشهد بأي مصدر منهم
    context_chunks = [
        {
            "index": e["rank"],
            "title": e["source_title"],
            "category": e["source_meta"].split("•")[0].strip(),
            "page": e["source_meta"].split("p.")[-1].strip(),
            "section": e["section_number"],
            "text": e["full_text"],
        }
        for e in evidence
    ]

    try:
        answer = llm.generate_answer(
            role=role,
            question=question,
            context_chunks=context_chunks,
            history=history,
            
        ) 
        answer = drug_names.add_egyptian_brand_names(answer)
    except Exception:
        answer = (
            "I found approved clinical sources, but the answer service is temporarily "
            "unavailable. Please try again shortly or discuss this with your care team."
        )
    return answer, evidence