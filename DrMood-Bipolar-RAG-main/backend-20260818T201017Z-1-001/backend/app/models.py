import uuid
from datetime import datetime

from sqlalchemy import Column, String, Text, DateTime, ForeignKey, Float, Integer
from sqlalchemy.orm import relationship

from app.database import Base


def gen_id() -> str:
    return uuid.uuid4().hex


class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(String, primary_key=True, default=gen_id)
    title = Column(String, default="New chat")
    role = Column(String, default="patient")  # "patient" | "doctor"
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan")


class Message(Base):
    __tablename__ = "messages"

    id = Column(String, primary_key=True, default=gen_id)
    conversation_id = Column(String, ForeignKey("conversations.id"), nullable=False)
    role = Column(String, nullable=False)  # "user" | "assistant"
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    conversation = relationship("Conversation", back_populates="messages")
    evidence = relationship("Evidence", back_populates="message", cascade="all, delete-orphan")


class Evidence(Base):
    """A single retrieved source chunk attached to an assistant message."""
    __tablename__ = "evidence"

    id = Column(String, primary_key=True, default=gen_id)
    message_id = Column(String, ForeignKey("messages.id"), nullable=False)

    source_title = Column(String, nullable=False)
    source_meta = Column(String, default="")       # e.g. "Mania • p. 12"
    snippet = Column(Text, default="")              # short summary shown on the card
    full_text = Column(Text, default="")             # text shown in the source preview panel
    score = Column(Float, default=0.0)
    used = Column(Integer, default=0)                # 1 = actually cited in the answer, 0 = supporting only
    rank = Column(Integer, default=0)

    message = relationship("Message", back_populates="evidence")


class ClinicalDocument(Base):
    """Metadata for an ingested clinical source document (the file itself lives in the vector store)."""
    __tablename__ = "clinical_documents"

    id = Column(String, primary_key=True, default=gen_id)
    title = Column(String, nullable=False)
    category = Column(String, default="")  # e.g. "Mania", "Bipolar I", "Treatment"
    page = Column(String, default="")
    chunk_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)


class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=gen_id)
    name = Column(String, nullable=False, default="")
    email = Column(String, nullable=False, unique=True, index=True)
    password_hash = Column(String, nullable=False)
    avatar_url = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
