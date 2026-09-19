from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.security import create_access_token, ensure_database_ready, get_current_user, hash_password, verify_password
from app.db.database import get_db, init_db
from app.db.models import User


router = APIRouter(prefix="/auth", tags=["auth"])


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str | None = Field(default=None, max_length=100)


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    id: str
    email: str
    full_name: str | None
    role: str
    is_active: bool


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


def _user_response(user: User) -> UserResponse:
    return UserResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        is_active=user.is_active,
    )


@router.post("/init-db")
def initialize_database() -> dict[str, str]:
    try:
        init_db()
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Failed to initialize database tables: {exc}",
        ) from exc
    return {"status": "ok", "message": "Database tables are ready."}


@router.post("/register", response_model=TokenResponse)
def register_user(payload: UserCreate, db: Annotated[Session, Depends(get_db)]) -> TokenResponse:
    ensure_database_ready()
    email = payload.email.lower().strip()
    existing = db.scalar(select(User).where(User.email == email))
    if existing is not None:
        raise HTTPException(status_code=409, detail="Email is already registered.")

    user = User(
        id=str(uuid.uuid4()),
        email=email,
        password_hash=hash_password(payload.password),
        full_name=payload.full_name,
        role="analyst",
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return TokenResponse(access_token=create_access_token(user), user=_user_response(user))


@router.post("/login", response_model=TokenResponse)
def login_user(payload: UserLogin, db: Annotated[Session, Depends(get_db)]) -> TokenResponse:
    ensure_database_ready()
    email = payload.email.lower().strip()
    user = db.scalar(select(User).where(User.email == email))
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password.")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="User is inactive.")
    return TokenResponse(access_token=create_access_token(user), user=_user_response(user))


@router.get("/me", response_model=UserResponse)
def get_me(current_user: Annotated[User, Depends(get_current_user)]) -> UserResponse:
    return _user_response(current_user)
