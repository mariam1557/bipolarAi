from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import Base, engine
from app.routers import auth, chat, conversations, documents

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Dr. Mood API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat.router)
app.include_router(auth.router)
app.include_router(conversations.router)
app.include_router(documents.router)


@app.get("/")
def root():
    return {"status": "ok", "service": "Dr. Mood API", "docs": "/docs"}


@app.get("/api/health")
def health():
    return {"status": "ok"}