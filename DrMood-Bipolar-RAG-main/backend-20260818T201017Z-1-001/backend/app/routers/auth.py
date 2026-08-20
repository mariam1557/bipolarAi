from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from jose import jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from app import models, schemas
from app.config import settings
from app.database import get_db

router = APIRouter(prefix="/api/auth", tags=["auth"])
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def _user_payload(user: models.User) -> dict:
    return {
        "id": user.id,
        "email": user.email,
        "name": user.name,
        "avatar_url": user.avatar_url,
    }


def _token_for(user: models.User) -> str:
    expires = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expire_minutes)
    return jwt.encode(
        {"sub": user.id, "exp": expires},
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
    )


def _response(user: models.User) -> dict:
    return {"access_token": _token_for(user), "token_type": "bearer", "user": _user_payload(user)}


@router.post("/register")
def register(payload: schemas.RegisterRequest, db: Session = Depends(get_db)):
    email = payload.email.strip().lower()
    if db.query(models.User).filter(models.User.email == email).first():
        raise HTTPException(status_code=409, detail="An account with this email already exists.")

    user = models.User(
        name=payload.name.strip() or email.split("@", 1)[0],
        email=email,
        password_hash=pwd_context.hash(payload.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return _response(user)


@router.post("/login")
def login(payload: schemas.AuthCredentials, db: Session = Depends(get_db)):
    email = payload.email.strip().lower()
    user = db.query(models.User).filter(models.User.email == email).first()
    if not user or not pwd_context.verify(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password.",
        )
    return _response(user)


@router.post("/google")
def google_login(payload: schemas.GoogleLoginRequest, db: Session = Depends(get_db)):
    if not settings.google_client_id:
        raise HTTPException(status_code=503, detail="Google sign-in is not configured.")

    try:
        from google.oauth2 import id_token
        from google.auth.transport import requests

        claims = id_token.verify_oauth2_token(
            payload.id_token,
            requests.Request(),
            settings.google_client_id,
        )
    except Exception as error:
        raise HTTPException(status_code=401, detail="Invalid Google sign-in token.") from error

    email = str(claims.get("email", "")).strip().lower()
    if not email or not claims.get("email_verified", False):
        raise HTTPException(status_code=401, detail="Google email is not verified.")

    user = db.query(models.User).filter(models.User.email == email).first()
    if not user:
        user = models.User(
            name=str(claims.get("name", "")).strip() or email.split("@", 1)[0],
            email=email,
            password_hash=pwd_context.hash("google:" + str(claims.get("sub", ""))),
            avatar_url=claims.get("picture"),
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    return _response(user)
