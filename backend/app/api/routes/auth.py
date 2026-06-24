"""Custom-JWT auth endpoints. Refresh tokens are stored hashed, support
rotation on refresh, and revocation on logout."""
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.config import settings
from app.core import security
from app.database import get_db
from app.models.user import RefreshToken, User
from app.schemas.auth import (AuthResponse, LoginRequest, RefreshRequest,
                              SignupRequest, TokenPair)
from app.schemas.user import UserOut

router = APIRouter(prefix="/auth", tags=["auth"])


def _issue_refresh(db: Session, user_id: str) -> str:
    raw, token_hash = security.generate_refresh_token()
    expires = datetime.now(timezone.utc) + timedelta(days=settings.refresh_token_expire_days)
    db.add(RefreshToken(user_id=user_id, token_hash=token_hash, expires_at=expires))
    db.commit()
    return raw


@router.post("/signup", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
def signup(payload: SignupRequest, db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == payload.email).first():
        raise HTTPException(status_code=409, detail="Email already registered")
    user = User(email=payload.email, hashed_password=security.hash_password(payload.password),
                display_name=payload.display_name, role=payload.role)
    db.add(user); db.commit(); db.refresh(user)
    access = security.create_access_token(user.id)
    refresh = _issue_refresh(db, user.id)
    return AuthResponse(access_token=access, refresh_token=refresh, user=UserOut.model_validate(user))


@router.post("/login", response_model=AuthResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email).first()
    if user is None or not security.verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    access = security.create_access_token(user.id)
    refresh = _issue_refresh(db, user.id)
    return AuthResponse(access_token=access, refresh_token=refresh, user=UserOut.model_validate(user))


@router.post("/refresh", response_model=TokenPair)
def refresh(payload: RefreshRequest, db: Session = Depends(get_db)):
    token_hash = security.hash_refresh_token(payload.refresh_token)
    rt = db.query(RefreshToken).filter(RefreshToken.token_hash == token_hash).first()
    now = datetime.now(timezone.utc)
    # SQLite returns naive datetimes even for timezone=True columns; normalize to UTC.
    expired = rt is not None and (
        rt.expires_at.replace(tzinfo=timezone.utc) if rt.expires_at.tzinfo is None else rt.expires_at
    ) < now
    if rt is None or rt.revoked or expired:
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")
    rt.revoked = True  # rotate: old token can't be reused
    db.commit()
    access = security.create_access_token(rt.user_id)
    new_refresh = _issue_refresh(db, rt.user_id)
    return TokenPair(access_token=access, refresh_token=new_refresh)


@router.post("/logout")
def logout(payload: RefreshRequest, db: Session = Depends(get_db)):
    token_hash = security.hash_refresh_token(payload.refresh_token)
    rt = db.query(RefreshToken).filter(RefreshToken.token_hash == token_hash).first()
    if rt:
        rt.revoked = True
        db.commit()
    return {"status": "logged_out"}


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    return UserOut.model_validate(user)
