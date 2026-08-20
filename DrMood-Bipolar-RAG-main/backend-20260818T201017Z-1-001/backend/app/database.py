from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

from app.config import settings

database_url = settings.database_url
connect_args = {}
if database_url.startswith("sqlite"):
    database_path = Path(database_url.removeprefix("sqlite:///"))
    if not database_path.is_absolute():
        database_path = Path(__file__).resolve().parents[2] / database_path
    database_url = f"sqlite:///{database_path.as_posix()}"
    connect_args = {"check_same_thread": False, "timeout": 30}

engine = create_engine(database_url, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
