from datetime import datetime
from typing import Literal, Optional, Any

from pydantic import BaseModel, Field


class AuthCredentials(BaseModel):
    email: str
    password: str = Field(..., min_length=8, max_length=128)


class RegisterRequest(AuthCredentials):
    name: str = Field(default="", max_length=120)


class GoogleLoginRequest(BaseModel):
    id_token: str


# ---------- Conversations ----------

class ConversationCreate(BaseModel):
    role: Literal["patient", "doctor"] = "patient"
    title: Optional[str] = None


class ConversationOut(BaseModel):
    id: str
    title: str
    role: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ---------- Evidence ----------

class EvidenceOut(BaseModel):
    id: str
    source_title: str
    source_meta: str
    snippet: str
    full_text: str
    score: float
    used: bool
    rank: int

    class Config:
        from_attributes = True


# ---------- Messages ----------

class MessageOut(BaseModel):
    id: str
    role: str
    content: str
    created_at: datetime
    evidence: list[EvidenceOut] = []

    class Config:
        from_attributes = True


# ---------- Chat ----------

class ChatRequest(BaseModel):
    conversation_id: Optional[str] = None
    role: Literal["patient", "doctor"] = "patient"
    message: str = Field(..., min_length=1, max_length=4000)


class ChatResponse(BaseModel):
    conversation_id: str
    message: Any
    crisis_flag: Optional[bool] = None
    confidence: Optional[str] = None
    confidence_color: Optional[str] = None


# ---------- Document ingestion ----------

class DocumentOut(BaseModel):
    id: str
    title: str
    category: str
    page: str
    chunk_count: int
    created_at: datetime

    class Config:
        from_attributes = True