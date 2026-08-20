from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


PROJECT_ENV_FILE = Path(__file__).resolve().parents[3] / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=PROJECT_ENV_FILE,
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # LLM
    gemini_api_key: str = "AQ.Ab8RN6JJTDiQhXYF9fu3sI0OP67IdPhz_dmvAaiFzvVCUTb2hw"
    llm_model: str = "gemini-3.6-flash"
    jwt_secret: str = "change-this-development-secret"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 1440
    google_client_id: str = ""

    # Database
    database_url: str = "sqlite:///./drmood.db"

    # Vector store
    chroma_persist_dir: str = "./chroma_store"
    chroma_collection: str = "clinical_sources"

    # Embeddings — gte-base was chosen after comparing 7 models on Precision@k in Day 2.
    # IMPORTANT: if you change this, delete chroma_store/ and re-run
    # `python -m app.seed_data.seed_nice` — a collection built with one embedding
    # model is not compatible with vectors from a different model (different dimensions).
    embedding_model: str = "thenlper/gte-base"

    # Retrieval
    retrieval_top_k: int = 5
    # Calibrated from app/eval_metrics.py on 2026-08-20: on-topic questions scored
    # 0.86-0.94 (top_score), out-of-scope questions scored 0.69-0.73. 0.78 sits in
    # the middle of that gap, so it accepts every real question in the eval set
    # while refusing every out-of-scope one. Re-run eval_metrics.py after any
    # embedding model or dataset change and re-check this gap still holds.
    retrieval_min_score: float = 0.78

    # CORS
    cors_origins: str = "http://localhost:5500,http://127.0.0.1:5500,http://localhost:5501,http://127.0.0.1:5501"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


settings = Settings()