from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app import models, schemas

router = APIRouter(prefix="/api/conversations", tags=["conversations"])


@router.get("", response_model=list[schemas.ConversationOut])
def list_conversations(db: Session = Depends(get_db)):
    convos = db.query(models.Conversation).order_by(models.Conversation.updated_at.desc()).all()
    return convos


@router.post("", response_model=schemas.ConversationOut)
def create_conversation(payload: schemas.ConversationCreate, db: Session = Depends(get_db)):
    convo = models.Conversation(title=payload.title or "New chat", role=payload.role)
    db.add(convo)
    db.commit()
    db.refresh(convo)
    return convo


@router.get("/{conversation_id}/messages", response_model=list[schemas.MessageOut])
def get_messages(conversation_id: str, db: Session = Depends(get_db)):
    convo = db.get(models.Conversation, conversation_id)
    if not convo:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return db.query(models.Message).filter(
        models.Message.conversation_id == conversation_id
    ).order_by(models.Message.created_at.asc()).all()


@router.delete("/{conversation_id}")
def delete_conversation(conversation_id: str, db: Session = Depends(get_db)):
    convo = db.get(models.Conversation, conversation_id)
    if not convo:
        raise HTTPException(status_code=404, detail="Conversation not found")
    db.delete(convo)
    db.commit()
    return {"ok": True}
