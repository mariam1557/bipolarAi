from io import BytesIO
from pathlib import Path

import arabic_reshaper
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from bidi.algorithm import get_display
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas
from sqlalchemy.orm import Session

from app.database import get_db
from app import models, schemas
from app.services import rag, safety

router = APIRouter(prefix="/api/chat", tags=["chat"])

CRISIS_RESOURCES_NOTE = (
    "It sounds like you might be going through something really painful right now. "
    "You deserve support — please consider reaching out to a crisis line or emergency "
    "services in your area right now, or contacting someone you trust so you're not alone with this.\n\n"
    "يبدو إنك بتمر بحاجة صعبة جداً دلوقتي. إنت تستاهل دعم — من فضلك حاول تتواصل مع خط أزمات "
    "أو خدمات الطوارئ في منطقتك حالاً، أو مع حد تثق فيه عشان متكونش لوحدك في اللي بتمر بيه."
)


def _compute_confidence(evidence: list[dict], crisis_flag: bool) -> tuple[str, str]:
    """بيحسب مستوى الثقة الفعلي بناءً على أعلى score في الـ evidence."""
    if crisis_flag:
        return "Low", "red"
    if not evidence:
        return "Low", "red"

    top_score = max(e["score"] for e in evidence)
    if top_score >= 0.75:
        return "High", "green"
    if top_score >= 0.5:
        return "Medium", "orange"
    return "Low", "red"


PDF_FONT_PATH = Path("C:/Windows/Fonts/arial.ttf")
PDF_FONT_NAME = "ArialUnicode"
if PDF_FONT_PATH.exists():
    pdfmetrics.registerFont(TTFont(PDF_FONT_NAME, str(PDF_FONT_PATH)))


def _pdf_text(value: str) -> str:
    """Shape Arabic text and preserve Unicode characters in the generated PDF."""
    if any("\u0600" <= char <= "\u06ff" for char in value):
        return get_display(arabic_reshaper.reshape(value))
    return value


def _draw_pdf_line(document, text: str, y: float, font_name: str) -> None:
    if any("\u0600" <= char <= "\u06ff" for char in text):
        document.drawRightString(550, y, text)
    else:
        document.drawString(50, y, text)


@router.get("/messages/{message_id}/pdf")
def download_message_pdf(message_id: str, db: Session = Depends(get_db)):
    message = db.get(models.Message, message_id)
    if not message:
        raise HTTPException(status_code=404, detail="Message not found")

    buffer = BytesIO()
    document = canvas.Canvas(buffer, pagesize=A4)
    _, page_height = A4
    y = page_height - 50

    document.setTitle("Dr. Mood conversation summary")
    font_name = PDF_FONT_NAME if PDF_FONT_PATH.exists() else "Helvetica"
    document.setFont(font_name, 16)
    document.drawString(50, y, "Dr. Mood - Conversation Summary")
    y -= 32
    document.setFont(font_name, 10)
    document.drawString(50, y, f"Message ID: {message.id}")
    y -= 24
    document.setFont(font_name, 11)
    document.drawString(50, y, "Answer")
    y -= 18
    document.setFont(font_name, 10)

    for paragraph in _pdf_text(message.content).splitlines() or [""]:
        words = paragraph.split()
        line = ""
        for word in words:
            candidate = f"{line} {word}".strip()
            if document.stringWidth(candidate, font_name, 10) > 500:
                _draw_pdf_line(document, line, y, font_name)
                y -= 14
                if y < 50:
                    document.showPage()
                    y = page_height - 50
                    document.setFont(font_name, 10)
                line = word
            else:
                line = candidate
        if line:
            _draw_pdf_line(document, line, y, font_name)
            y -= 14
        if y < 50:
            document.showPage()
            y = page_height - 50
            document.setFont(font_name, 10)

    if message.evidence:
        y -= 12
        document.setFont(font_name, 11)
        document.drawString(50, y, "Supporting sources")
        y -= 18
        document.setFont(font_name, 10)
        for item in message.evidence:
            source = _pdf_text(f"[{item.rank}] {item.source_title} - {item.source_meta}")
            _draw_pdf_line(document, source[:100], y, font_name)
            y -= 14
            if y < 50:
                document.showPage()
                y = page_height - 50
                document.setFont(font_name, 10)

    document.save()
    buffer.seek(0)
    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="drmood_{message.id[:8]}.pdf"'},
    )


@router.post("", response_model=schemas.ChatResponse)
def chat(payload: schemas.ChatRequest, db: Session = Depends(get_db)):
    # 1. Resolve or create the conversation
    if payload.conversation_id:
        convo = db.get(models.Conversation, payload.conversation_id)
        if not convo:
            raise HTTPException(status_code=404, detail="Conversation not found")
        convo.role = payload.role
    else:
        title = payload.message.strip()[:60] or "New chat"
        convo = models.Conversation(title=title, role=payload.role)
        db.add(convo)
        db.flush()

    # 2. Persist the user's message
    user_msg = models.Message(conversation_id=convo.id, role="user", content=payload.message)
    db.add(user_msg)
    db.flush()

    # 3. Build short conversational history for the LLM (last 10 turns)
    prior = db.query(models.Message).filter(
        models.Message.conversation_id == convo.id
    ).order_by(models.Message.created_at.asc()).all()
    history = [{"role": m.role, "content": m.content} for m in prior[-10:] if m.id != user_msg.id]

    crisis_flag = safety.is_potential_crisis(payload.message)

    # 4. RAG: retrieve evidence + generate a grounded answer
    answer_text, evidence = rag.answer_question(role=payload.role, question=payload.message, history=history)
    if crisis_flag:
        answer_text = f"{CRISIS_RESOURCES_NOTE}\n\n{answer_text}"

    # 5. Persist the assistant's message + evidence
    assistant_msg = models.Message(conversation_id=convo.id, role="assistant", content=answer_text)
    db.add(assistant_msg)
    db.flush()

    # نضيف الـ evidence كلها الأول من غير ما نبني الـ output، عشان الـ id يتحدد
    ev_pairs = []
    for e in evidence:
        ev_model = models.Evidence(
            message_id=assistant_msg.id,
            source_title=e["source_title"],
            source_meta=e["source_meta"],
            snippet=e["snippet"],
            full_text=e["full_text"],
            score=e["score"],
            used=1 if e["used"] else 0,
            rank=e["rank"],
        )
        db.add(ev_model)
        ev_pairs.append((ev_model, e))

    db.flush()  # دلوقتي كل ev_model.id بقى موجود فعلاً

    evidence_out_list = [
        {
            "id": str(ev_model.id),
            "source_title": e["source_title"],
            "source_meta": e["source_meta"],
            "snippet": e["snippet"],
            "full_text": e["full_text"],
            "score": e["score"],
            "used": bool(e["used"]),
            "rank": e["rank"],
        }
        for ev_model, e in ev_pairs
    ]

    confidence, confidence_color = _compute_confidence(evidence, crisis_flag)

    db.commit()
    db.refresh(assistant_msg)

    return schemas.ChatResponse(
        conversation_id=str(convo.id),
        message={
            "id": str(assistant_msg.id),
            "role": assistant_msg.role,
            "content": assistant_msg.content,
            "created_at": str(assistant_msg.created_at),
            "evidence": evidence_out_list,
        },
        crisis_flag=crisis_flag,
        confidence=confidence,
        confidence_color=confidence_color,
    )