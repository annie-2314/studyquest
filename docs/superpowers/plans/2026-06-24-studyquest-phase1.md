# StudyQuest AI — Phase 1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a running, deployable Phase 1 shell — animated landing page, custom-JWT auth, and a SQLite/Postgres-ready database — that a fresh machine can run natively with no paid API keys.

**Architecture:** A FastAPI backend (SQLAlchemy 2.0 + Alembic + Pydantic v2) exposes JWT auth + health endpoints. A Next.js 14 (App Router) + TypeScript + Tailwind + Framer Motion frontend renders the landing page and auth UI, talking to the backend through a typed fetch wrapper and a React auth context. Database engine is chosen from a single `DATABASE_URL` so SQLite (dev) and Postgres (prod) are interchangeable.

**Tech Stack:** FastAPI, SQLAlchemy 2.0, Alembic, Pydantic v2 / pydantic-settings, python-jose, passlib[bcrypt], pytest, httpx; Next.js 14, TypeScript, Tailwind CSS, Framer Motion.

## Global Constraints

- Python 3.11+; Node 18+.
- All secrets via environment variables only — never hardcoded. Provide `.env.example` / `.env.local.example`.
- `.gitignore` must exclude `.env`, `*.db`, `node_modules`, `__pycache__`, `.next`, `.venv`.
- Backend API base path: `/api`. CORS allows the frontend origin from `FRONTEND_ORIGIN` env (default `http://localhost:3000`).
- TypeScript strict mode on. Pydantic v2 models for all request/response DTOs.
- Error responses use shape `{"detail": str, "code": str}`.
- Product name string is exactly `StudyQuest AI`.
- No LLM/agent code in Phase 1.

---

### Task 1: Backend scaffold — config, database, app, health endpoint

**Files:**
- Create: `backend/requirements.txt`
- Create: `backend/app/__init__.py`
- Create: `backend/app/config.py`
- Create: `backend/app/database.py`
- Create: `backend/app/main.py`
- Create: `backend/app/api/__init__.py`
- Create: `backend/app/api/routes/__init__.py`
- Create: `backend/app/api/routes/health.py`
- Create: `backend/tests/__init__.py`
- Test: `backend/tests/test_health.py`

**Interfaces:**
- Produces: `app.config.settings` (pydantic-settings instance with `database_url`, `secret_key`, `access_token_expire_minutes`, `refresh_token_expire_days`, `frontend_origin`, `algorithm`); `app.database.Base`, `app.database.get_db()`, `app.database.engine`, `app.database.SessionLocal`; `app.main.app` (FastAPI instance); `GET /api/health` → `{"status": "ok"}`.

- [ ] **Step 1: Create `backend/requirements.txt`**

```
fastapi==0.115.0
uvicorn[standard]==0.30.6
sqlalchemy==2.0.35
alembic==1.13.2
pydantic==2.9.2
pydantic-settings==2.5.2
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
bcrypt==4.0.1
python-multipart==0.0.9
pytest==8.3.3
httpx==0.27.2
email-validator==2.2.0
```

- [ ] **Step 2: Create package init files**

`backend/app/__init__.py`, `backend/app/api/__init__.py`, `backend/app/api/routes/__init__.py`, `backend/tests/__init__.py` — each an empty file.

- [ ] **Step 3: Create `backend/app/config.py`**

```python
"""Application settings loaded from environment / .env (pydantic-settings)."""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # SQLite for dev (zero install); swap to a Postgres URL in prod, no code change.
    database_url: str = "sqlite:///./studyquest.db"
    secret_key: str = "dev-insecure-change-me"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7
    frontend_origin: str = "http://localhost:3000"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
```

- [ ] **Step 4: Create `backend/app/database.py`**

```python
"""SQLAlchemy engine/session. Engine is chosen from settings.database_url so
SQLite (dev) and Postgres (prod) are interchangeable with no code change."""
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from app.config import settings

# check_same_thread is only needed for SQLite under FastAPI's threadpool.
connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
engine = create_engine(settings.database_url, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    """FastAPI dependency yielding a DB session that always closes."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

- [ ] **Step 5: Create `backend/app/api/routes/health.py`**

```python
from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
def health():
    return {"status": "ok"}
```

- [ ] **Step 6: Create `backend/app/main.py`**

```python
"""FastAPI app: CORS, routers, and a consistent JSON error shape {detail, code}."""
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.config import settings
from app.api.routes import health

app = FastAPI(title="StudyQuest AI")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    return JSONResponse(status_code=exc.status_code,
                        content={"detail": exc.detail, "code": f"http_{exc.status_code}"})


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(status_code=422,
                        content={"detail": "Invalid request data", "code": "validation_error"})


app.include_router(health.router, prefix="/api")
```

- [ ] **Step 7: Write the failing test `backend/tests/test_health.py`**

```python
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health_returns_ok():
    resp = client.get("/api/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}
```

- [ ] **Step 8: Install deps and run the test**

Run (from `backend/`): `python -m venv .venv && . .venv/Scripts/activate && pip install -r requirements.txt && pytest tests/test_health.py -v`
Expected: PASS (1 passed).

- [ ] **Step 9: Commit**

```bash
git add backend/
git commit -m "feat(backend): scaffold FastAPI app, config, db session, health endpoint"
```

---

### Task 2: User & RefreshToken models + Alembic migration

**Files:**
- Create: `backend/app/models/__init__.py`
- Create: `backend/app/models/user.py`
- Create: `backend/alembic.ini`
- Create: `backend/alembic/env.py`
- Create: `backend/alembic/script.py.mako`
- Create: `backend/alembic/versions/0001_initial.py`
- Test: `backend/tests/test_models.py`

**Interfaces:**
- Consumes: `app.database.Base`, `app.database.engine`, `app.database.SessionLocal`.
- Produces: `app.models.user.User` (columns: `id:str`, `email:str`, `hashed_password:str`, `display_name:str`, `role:str`, `is_active:bool`, `created_at`, `updated_at`); `app.models.user.RefreshToken` (`id:str`, `user_id:str`, `token_hash:str`, `expires_at`, `revoked:bool`, `created_at`); `app.models.user.UserRole` constants `STUDENT/TEACHER/PARENT`.

- [ ] **Step 1: Create `backend/app/models/user.py`**

```python
"""ORM models for Phase 1: User and RefreshToken."""
import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.now(timezone.utc)


class UserRole:
    STUDENT = "student"
    TEACHER = "teacher"
    PARENT = "parent"


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    email: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String, nullable=False)
    display_name: Mapped[str] = mapped_column(String, nullable=False)
    role: Mapped[str] = mapped_column(String, default=UserRole.STUDENT, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now)

    refresh_tokens: Mapped[list["RefreshToken"]] = relationship(
        back_populates="user", cascade="all, delete-orphan")


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(String, ForeignKey("users.id"), nullable=False)
    token_hash: Mapped[str] = mapped_column(String, nullable=False, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    user: Mapped["User"] = relationship(back_populates="refresh_tokens")
```

- [ ] **Step 2: Create `backend/app/models/__init__.py`**

```python
from app.models.user import User, RefreshToken, UserRole  # noqa: F401
```

- [ ] **Step 3: Initialize Alembic config `backend/alembic.ini`**

Run (from `backend/`): `alembic init alembic`
Then in `alembic.ini`, leave `sqlalchemy.url` blank (env.py supplies it).

- [ ] **Step 4: Edit `backend/alembic/env.py` to use app metadata + settings URL**

Replace the body so it imports our config + metadata:

```python
from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context

from app.config import settings
from app.database import Base
import app.models  # noqa: F401  ensures models register on Base.metadata

config = context.config
config.set_main_option("sqlalchemy.url", settings.database_url)
if config.config_file_name is not None:
    fileConfig(config.config_file_name)
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    context.configure(url=settings.database_url, target_metadata=target_metadata,
                       literal_binds=True, dialect_opts={"paramstyle": "named"})
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(config.get_section(config.config_ini_section, {}),
                                     prefix="sqlalchemy.", poolclass=pool.NullPool)
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata,
                          render_as_batch=True)  # batch mode = SQLite ALTER support
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
```

- [ ] **Step 5: Autogenerate the initial migration**

Run (from `backend/`): `alembic revision --autogenerate -m "initial" `
Rename the generated file to `backend/alembic/versions/0001_initial.py` for clarity. Confirm it creates `users` and `refresh_tokens`.

- [ ] **Step 6: Write the failing test `backend/tests/test_models.py`**

```python
from datetime import datetime, timedelta, timezone

from app.database import Base, engine, SessionLocal
from app.models.user import User, RefreshToken, UserRole


def setup_module():
    Base.metadata.create_all(bind=engine)


def test_create_user_and_token():
    db = SessionLocal()
    user = User(email="a@b.com", hashed_password="x", display_name="A", role=UserRole.STUDENT)
    db.add(user)
    db.commit()
    db.refresh(user)
    assert user.id and user.is_active is True and user.role == "student"

    rt = RefreshToken(user_id=user.id, token_hash="h",
                      expires_at=datetime.now(timezone.utc) + timedelta(days=1))
    db.add(rt)
    db.commit()
    db.refresh(rt)
    assert rt.revoked is False and rt.user_id == user.id
    db.close()
```

- [ ] **Step 7: Run the test**

Run (from `backend/`): `pytest tests/test_models.py -v`
Expected: PASS.

- [ ] **Step 8: Apply migration and confirm schema**

Run (from `backend/`): `alembic upgrade head`
Expected: creates `studyquest.db` with `users` + `refresh_tokens` tables, no errors.

- [ ] **Step 9: Commit**

```bash
git add backend/
git commit -m "feat(backend): add User/RefreshToken models + initial Alembic migration"
```

---

### Task 3: Security core — password hashing + JWT (TDD)

**Files:**
- Create: `backend/app/core/__init__.py`
- Create: `backend/app/core/security.py`
- Test: `backend/tests/test_security.py`

**Interfaces:**
- Consumes: `app.config.settings`.
- Produces: `hash_password(p:str)->str`; `verify_password(p:str, h:str)->bool`; `create_access_token(subject:str)->str`; `decode_token(token:str)->dict` (raises `jose.JWTError` on invalid); `generate_refresh_token()->tuple[str,str]` returning `(raw, sha256_hash)`; `hash_refresh_token(raw:str)->str`.

- [ ] **Step 1: Write the failing test `backend/tests/test_security.py`**

```python
import pytest
from jose import JWTError

from app.core import security


def test_password_hash_roundtrip():
    h = security.hash_password("secret123")
    assert h != "secret123"
    assert security.verify_password("secret123", h) is True
    assert security.verify_password("wrong", h) is False


def test_access_token_roundtrip():
    token = security.create_access_token("user-id-1")
    payload = security.decode_token(token)
    assert payload["sub"] == "user-id-1"
    assert payload["type"] == "access"


def test_decode_invalid_token_raises():
    with pytest.raises(JWTError):
        security.decode_token("not.a.jwt")


def test_refresh_token_hash_is_deterministic():
    raw, h = security.generate_refresh_token()
    assert security.hash_refresh_token(raw) == h
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_security.py -v`
Expected: FAIL (module `app.core.security` not found).

- [ ] **Step 3: Create `backend/app/core/__init__.py`** (empty file)

- [ ] **Step 4: Create `backend/app/core/security.py`**

```python
"""Password hashing (bcrypt) and JWT helpers. Refresh tokens are random and
stored only as a SHA-256 hash so a DB leak never exposes usable tokens."""
import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from jose import jwt
from passlib.context import CryptContext

from app.config import settings

_pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return _pwd.hash(password)


def verify_password(password: str, hashed: str) -> bool:
    return _pwd.verify(password, hashed)


def create_access_token(subject: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes)
    payload = {"sub": subject, "type": "access", "exp": expire}
    return jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)


def decode_token(token: str) -> dict:
    return jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])


def hash_refresh_token(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


def generate_refresh_token() -> tuple[str, str]:
    raw = secrets.token_urlsafe(48)
    return raw, hash_refresh_token(raw)
```

- [ ] **Step 5: Run test to verify it passes**

Run: `pytest tests/test_security.py -v`
Expected: PASS (4 passed).

- [ ] **Step 6: Commit**

```bash
git add backend/app/core backend/tests/test_security.py
git commit -m "feat(backend): add bcrypt + JWT security core"
```

---

### Task 4: Auth schemas + current-user dependency

**Files:**
- Create: `backend/app/schemas/__init__.py`
- Create: `backend/app/schemas/auth.py`
- Create: `backend/app/schemas/user.py`
- Create: `backend/app/api/deps.py`
- Test: `backend/tests/test_deps.py`

**Interfaces:**
- Consumes: `app.core.security.decode_token`, `app.database.get_db`, `app.models.user.User`.
- Produces: Pydantic models `SignupRequest(email:EmailStr, password:str, display_name:str, role:str="student")`, `LoginRequest(email:EmailStr, password:str)`, `RefreshRequest(refresh_token:str)`, `TokenPair(access_token:str, refresh_token:str, token_type:str="bearer")`, `AuthResponse(access_token, refresh_token, token_type, user:UserOut)`, `UserOut(id, email, display_name, role, created_at)`; dependency `get_current_user(...) -> User`.

- [ ] **Step 1: Create `backend/app/schemas/__init__.py`** (empty file)

- [ ] **Step 2: Create `backend/app/schemas/user.py`**

```python
from datetime import datetime
from pydantic import BaseModel, ConfigDict


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    email: str
    display_name: str
    role: str
    created_at: datetime
```

- [ ] **Step 3: Create `backend/app/schemas/auth.py`**

```python
from pydantic import BaseModel, EmailStr, Field

from app.schemas.user import UserOut


class SignupRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    display_name: str = Field(min_length=1, max_length=80)
    role: str = "student"


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class AuthResponse(TokenPair):
    user: UserOut
```

- [ ] **Step 4: Create `backend/app/api/deps.py`**

```python
"""Auth dependency: resolve the current user from a Bearer access token."""
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlalchemy.orm import Session

from app.core.security import decode_token
from app.database import get_db
from app.models.user import User

_bearer = HTTPBearer(auto_error=False)


def get_current_user(
    creds: HTTPAuthorizationCredentials = Depends(_bearer),
    db: Session = Depends(get_db),
) -> User:
    if creds is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        payload = decode_token(creds.credentials)
        if payload.get("type") != "access":
            raise HTTPException(status_code=401, detail="Invalid token type")
        user_id = payload["sub"]
    except (JWTError, KeyError):
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    user = db.query(User).filter(User.id == user_id).first()
    if user is None or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found or inactive")
    return user
```

- [ ] **Step 5: Write the failing test `backend/tests/test_deps.py`**

```python
import pytest
from fastapi import HTTPException

from app.api.deps import get_current_user
from app.core.security import create_access_token
from app.database import Base, engine, SessionLocal
from app.models.user import User


def setup_module():
    Base.metadata.create_all(bind=engine)


class _Creds:
    def __init__(self, token):
        self.credentials = token


def test_get_current_user_valid():
    db = SessionLocal()
    u = User(email="d@e.com", hashed_password="x", display_name="D")
    db.add(u); db.commit(); db.refresh(u)
    token = create_access_token(u.id)
    result = get_current_user(creds=_Creds(token), db=db)
    assert result.id == u.id
    db.close()


def test_get_current_user_no_creds():
    db = SessionLocal()
    with pytest.raises(HTTPException) as exc:
        get_current_user(creds=None, db=db)
    assert exc.value.status_code == 401
    db.close()
```

- [ ] **Step 6: Run the test**

Run: `pytest tests/test_deps.py -v`
Expected: PASS (2 passed).

- [ ] **Step 7: Commit**

```bash
git add backend/app/schemas backend/app/api/deps.py backend/tests/test_deps.py
git commit -m "feat(backend): add auth schemas + current-user dependency"
```

---

### Task 5: Auth endpoints — signup/login/refresh/logout/me (TDD)

**Files:**
- Create: `backend/app/api/routes/auth.py`
- Modify: `backend/app/main.py` (include auth router)
- Test: `backend/tests/test_auth_api.py`

**Interfaces:**
- Consumes: schemas from Task 4, `security.*` from Task 3, `get_current_user`, `get_db`, models.
- Produces: routes `POST /api/auth/signup`, `POST /api/auth/login`, `POST /api/auth/refresh`, `POST /api/auth/logout`, `GET /api/auth/me`.

- [ ] **Step 1: Write the failing test `backend/tests/test_auth_api.py`**

```python
import pytest
from fastapi.testclient import TestClient

from app.database import Base, engine
from app.main import app

client = TestClient(app)


def setup_module():
    Base.metadata.create_all(bind=engine)


def _signup(email="u1@x.com"):
    return client.post("/api/auth/signup", json={
        "email": email, "password": "supersecret", "display_name": "U1"})


def test_signup_returns_tokens_and_user():
    r = _signup("new@x.com")
    assert r.status_code == 201
    body = r.json()
    assert body["access_token"] and body["refresh_token"]
    assert body["user"]["email"] == "new@x.com"


def test_duplicate_email_conflict():
    _signup("dup@x.com")
    r = _signup("dup@x.com")
    assert r.status_code == 409
    assert r.json()["code"] == "http_409"


def test_login_success_and_wrong_password():
    _signup("login@x.com")
    ok = client.post("/api/auth/login", json={"email": "login@x.com", "password": "supersecret"})
    assert ok.status_code == 200 and ok.json()["access_token"]
    bad = client.post("/api/auth/login", json={"email": "login@x.com", "password": "nope12345"})
    assert bad.status_code == 401


def test_me_requires_token():
    assert client.get("/api/auth/me").status_code == 401
    token = _signup("me@x.com").json()["access_token"]
    r = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200 and r.json()["email"] == "me@x.com"


def test_refresh_and_logout():
    rt = _signup("ref@x.com").json()["refresh_token"]
    refreshed = client.post("/api/auth/refresh", json={"refresh_token": rt})
    assert refreshed.status_code == 200 and refreshed.json()["access_token"]
    out = client.post("/api/auth/logout", json={"refresh_token": rt})
    assert out.status_code == 200
    # revoked token can no longer refresh
    assert client.post("/api/auth/refresh", json={"refresh_token": rt}).status_code == 401
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_auth_api.py -v`
Expected: FAIL (404s — routes not defined).

- [ ] **Step 3: Create `backend/app/api/routes/auth.py`**

```python
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
    if rt is None or rt.revoked or rt.expires_at < now:
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
```

- [ ] **Step 4: Include the auth router in `backend/app/main.py`**

Add import and include:

```python
from app.api.routes import health, auth
# ... after the health include:
app.include_router(auth.router, prefix="/api")
```

- [ ] **Step 5: Run the test to verify it passes**

Run: `pytest tests/test_auth_api.py -v`
Expected: PASS (5 passed).

- [ ] **Step 6: Run the full backend suite**

Run: `pytest -v`
Expected: all tests pass.

- [ ] **Step 7: Commit**

```bash
git add backend/
git commit -m "feat(backend): add signup/login/refresh/logout/me auth endpoints"
```

---

### Task 6: Frontend scaffold — Next.js + Tailwind + fonts + theme

**Files:**
- Create: `frontend/package.json`
- Create: `frontend/tsconfig.json`
- Create: `frontend/next.config.mjs`
- Create: `frontend/postcss.config.mjs`
- Create: `frontend/tailwind.config.ts`
- Create: `frontend/app/globals.css`
- Create: `frontend/app/layout.tsx`
- Create: `frontend/app/page.tsx` (temporary placeholder, replaced in Task 8)
- Create: `frontend/.env.local.example`

**Interfaces:**
- Produces: a running Next.js app on `http://localhost:3000`; Tailwind theme tokens `quest.bg`, `quest.violet`, `quest.lime`, `quest.cyan`, `quest.text`; fonts Space Grotesk (`--font-display`) + Inter (`--font-body`); env var `NEXT_PUBLIC_API_BASE` (default `http://localhost:8000/api`).

- [ ] **Step 1: Create `frontend/package.json`**

```json
{
  "name": "studyquest-frontend",
  "version": "0.1.0",
  "private": true,
  "scripts": {
    "dev": "next dev",
    "build": "next build",
    "start": "next start",
    "lint": "next lint"
  },
  "dependencies": {
    "next": "14.2.5",
    "react": "18.3.1",
    "react-dom": "18.3.1",
    "framer-motion": "11.3.19"
  },
  "devDependencies": {
    "typescript": "5.5.4",
    "@types/node": "20.14.12",
    "@types/react": "18.3.3",
    "@types/react-dom": "18.3.0",
    "tailwindcss": "3.4.7",
    "postcss": "8.4.40",
    "autoprefixer": "10.4.19"
  }
}
```

- [ ] **Step 2: Create `frontend/tsconfig.json`**

```json
{
  "compilerOptions": {
    "target": "ES2020",
    "lib": ["dom", "dom.iterable", "esnext"],
    "allowJs": true,
    "skipLibCheck": true,
    "strict": true,
    "noEmit": true,
    "esModuleInterop": true,
    "module": "esnext",
    "moduleResolution": "bundler",
    "resolveJsonModule": true,
    "isolatedModules": true,
    "jsx": "preserve",
    "incremental": true,
    "plugins": [{ "name": "next" }],
    "paths": { "@/*": ["./*"] }
  },
  "include": ["next-env.d.ts", "**/*.ts", "**/*.tsx", ".next/types/**/*.ts"],
  "exclude": ["node_modules"]
}
```

- [ ] **Step 3: Create `frontend/next.config.mjs`**

```js
/** @type {import('next').NextConfig} */
const nextConfig = { reactStrictMode: true };
export default nextConfig;
```

- [ ] **Step 4: Create `frontend/postcss.config.mjs`**

```js
export default { plugins: { tailwindcss: {}, autoprefixer: {} } };
```

- [ ] **Step 5: Create `frontend/tailwind.config.ts`**

```ts
import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        quest: {
          bg: "#0E0B1E",
          surface: "#171231",
          violet: "#7C3AED",
          lime: "#A3E635",
          cyan: "#22D3EE",
          text: "#F5F3FF",
          muted: "#A89FC9",
        },
      },
      fontFamily: {
        display: ["var(--font-display)", "system-ui", "sans-serif"],
        body: ["var(--font-body)", "system-ui", "sans-serif"],
      },
    },
  },
  plugins: [],
};
export default config;
```

- [ ] **Step 6: Create `frontend/app/globals.css`**

```css
@tailwind base;
@tailwind components;
@tailwind utilities;

body {
  background-color: theme('colors.quest.bg');
  color: theme('colors.quest.text');
  font-family: var(--font-body), system-ui, sans-serif;
}
```

- [ ] **Step 7: Create `frontend/app/layout.tsx`**

```tsx
import type { Metadata } from "next";
import { Inter, Space_Grotesk } from "next/font/google";
import "./globals.css";

const display = Space_Grotesk({ subsets: ["latin"], variable: "--font-display" });
const body = Inter({ subsets: ["latin"], variable: "--font-body" });

export const metadata: Metadata = {
  title: "StudyQuest AI",
  description: "An AI tutor that turns any course into a gamified, trackable quest.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`${display.variable} ${body.variable}`}>
      <body>{children}</body>
    </html>
  );
}
```

- [ ] **Step 8: Create temporary `frontend/app/page.tsx`**

```tsx
export default function Home() {
  return <main className="p-10 font-display text-2xl">StudyQuest AI — scaffold OK</main>;
}
```

- [ ] **Step 9: Create `frontend/.env.local.example`**

```
NEXT_PUBLIC_API_BASE=http://localhost:8000/api
```

- [ ] **Step 10: Install and run**

Run (from `frontend/`): `npm install && npm run dev`
Expected: dev server on `http://localhost:3000` shows "StudyQuest AI — scaffold OK" in Space Grotesk on the dark theme.

- [ ] **Step 11: Commit**

```bash
git add frontend/ '!frontend/node_modules'
git commit -m "feat(frontend): scaffold Next.js + Tailwind + quest theme + fonts"
```

---

### Task 7: API client + auth context

**Files:**
- Create: `frontend/lib/api.ts`
- Create: `frontend/lib/auth.tsx`
- Modify: `frontend/app/layout.tsx` (wrap children in `<AuthProvider>`)

**Interfaces:**
- Produces: `apiFetch<T>(path, opts?) -> Promise<T>` throwing `ApiError {detail, code, status}` on non-2xx; types `User`, `AuthResponse`; `AuthProvider` component; `useAuth()` hook returning `{user, loading, login, signup, logout}`.

- [ ] **Step 1: Create `frontend/lib/api.ts`**

```ts
const BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000/api";

export class ApiError extends Error {
  constructor(public detail: string, public code: string, public status: number) {
    super(detail);
  }
}

export interface User {
  id: string; email: string; display_name: string; role: string; created_at: string;
}
export interface AuthResponse {
  access_token: string; refresh_token: string; token_type: string; user: User;
}

export async function apiFetch<T>(path: string, opts: RequestInit = {}, token?: string): Promise<T> {
  const headers: Record<string, string> = { "Content-Type": "application/json", ...(opts.headers as Record<string, string>) };
  if (token) headers["Authorization"] = `Bearer ${token}`;
  let resp: Response;
  try {
    resp = await fetch(`${BASE}${path}`, { ...opts, headers });
  } catch {
    throw new ApiError("Cannot reach the server. Is the backend running?", "network_error", 0);
  }
  if (!resp.ok) {
    const body = await resp.json().catch(() => ({ detail: "Request failed", code: "unknown" }));
    throw new ApiError(body.detail ?? "Request failed", body.code ?? "unknown", resp.status);
  }
  return resp.json() as Promise<T>;
}
```

- [ ] **Step 2: Create `frontend/lib/auth.tsx`**

```tsx
"use client";
import { createContext, useCallback, useContext, useEffect, useState } from "react";
import { apiFetch, AuthResponse, User } from "./api";

interface AuthState {
  user: User | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  signup: (email: string, password: string, display_name: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthState | null>(null);
const ACCESS_KEY = "sq_access";
const REFRESH_KEY = "sq_refresh";

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  const loadMe = useCallback(async () => {
    const token = localStorage.getItem(ACCESS_KEY);
    if (!token) { setLoading(false); return; }
    try {
      const me = await apiFetch<User>("/auth/me", {}, token);
      setUser(me);
    } catch {
      localStorage.removeItem(ACCESS_KEY);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { loadMe(); }, [loadMe]);

  function persist(res: AuthResponse) {
    localStorage.setItem(ACCESS_KEY, res.access_token);
    localStorage.setItem(REFRESH_KEY, res.refresh_token);
    setUser(res.user);
  }

  const login = async (email: string, password: string) => {
    persist(await apiFetch<AuthResponse>("/auth/login", { method: "POST", body: JSON.stringify({ email, password }) }));
  };
  const signup = async (email: string, password: string, display_name: string) => {
    persist(await apiFetch<AuthResponse>("/auth/signup", { method: "POST", body: JSON.stringify({ email, password, display_name }) }));
  };
  const logout = () => {
    const rt = localStorage.getItem(REFRESH_KEY);
    if (rt) apiFetch("/auth/logout", { method: "POST", body: JSON.stringify({ refresh_token: rt }) }).catch(() => {});
    localStorage.removeItem(ACCESS_KEY);
    localStorage.removeItem(REFRESH_KEY);
    setUser(null);
  };

  return <AuthContext.Provider value={{ user, loading, login, signup, logout }}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
```

- [ ] **Step 3: Wrap layout in `frontend/app/layout.tsx`**

Import and wrap: change `<body>{children}</body>` to:

```tsx
import { AuthProvider } from "@/lib/auth";
// ...
<body><AuthProvider>{children}</AuthProvider></body>
```

- [ ] **Step 4: Verify it compiles**

Run (from `frontend/`): `npm run build`
Expected: build succeeds with no type errors.

- [ ] **Step 5: Commit**

```bash
git add frontend/lib frontend/app/layout.tsx
git commit -m "feat(frontend): add typed API client + auth context"
```

---

### Task 8: Landing page components

**Files:**
- Create: `frontend/components/ui/Button.tsx`
- Create: `frontend/components/landing/Nav.tsx`
- Create: `frontend/components/landing/Hero.tsx`
- Create: `frontend/components/landing/Features.tsx`
- Create: `frontend/components/landing/HowItWorks.tsx`
- Create: `frontend/components/landing/DemoPreview.tsx`
- Create: `frontend/components/landing/Footer.tsx`
- Modify: `frontend/app/page.tsx` (compose the landing page)

**Interfaces:**
- Consumes: Framer Motion, theme tokens.
- Produces: default-exported React components; `app/page.tsx` renders Nav + Hero + Features + HowItWorks + DemoPreview + Footer.

- [ ] **Step 1: Create `frontend/components/ui/Button.tsx`**

```tsx
import Link from "next/link";

export function Button({ href, children, variant = "primary" }:
  { href: string; children: React.ReactNode; variant?: "primary" | "ghost" }) {
  const base = "inline-flex items-center justify-center rounded-xl px-6 py-3 font-display font-medium transition-transform hover:scale-105";
  const styles = variant === "primary"
    ? "bg-quest-violet text-white shadow-lg shadow-quest-violet/30"
    : "border border-quest-muted/40 text-quest-text hover:border-quest-cyan";
  return <Link href={href} className={`${base} ${styles}`}>{children}</Link>;
}
```

- [ ] **Step 2: Create `frontend/components/landing/Nav.tsx`**

```tsx
import Link from "next/link";
import { Button } from "@/components/ui/Button";

export default function Nav() {
  return (
    <nav className="flex items-center justify-between px-6 py-5 md:px-12">
      <Link href="/" className="font-display text-xl font-bold">
        Study<span className="text-quest-lime">Quest</span> AI
      </Link>
      <div className="flex items-center gap-3">
        <Link href="/login" className="text-quest-muted hover:text-quest-text">Log in</Link>
        <Button href="/signup">Start your quest</Button>
      </div>
    </nav>
  );
}
```

- [ ] **Step 3: Create `frontend/components/landing/Hero.tsx`**

```tsx
"use client";
import { motion } from "framer-motion";
import { Button } from "@/components/ui/Button";

export default function Hero() {
  return (
    <section className="relative overflow-hidden px-6 py-24 text-center md:px-12">
      <motion.div
        className="pointer-events-none absolute left-1/2 top-10 h-72 w-72 -translate-x-1/2 rounded-full bg-quest-violet/30 blur-3xl"
        animate={{ scale: [1, 1.2, 1] }} transition={{ duration: 6, repeat: Infinity }} />
      <motion.h1
        initial={{ opacity: 0, y: 24 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.6 }}
        className="font-display text-5xl font-bold leading-tight md:text-7xl">
        Turn any course into a <span className="text-quest-lime">quest</span>.
      </motion.h1>
      <motion.p
        initial={{ opacity: 0, y: 24 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.6, delay: 0.15 }}
        className="mx-auto mt-6 max-w-2xl text-lg text-quest-muted">
        An AI tutor that explains anything, turns YouTube courses into trackable roadmaps,
        remembers your weak spots, and levels you up as you learn.
      </motion.p>
      <motion.div
        initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.35 }}
        className="mt-10 flex justify-center gap-4">
        <Button href="/signup">Start your quest</Button>
        <Button href="#how" variant="ghost">See how it works</Button>
      </motion.div>
    </section>
  );
}
```

- [ ] **Step 4: Create `frontend/components/landing/Features.tsx`**

```tsx
"use client";
import { motion } from "framer-motion";

const FEATURES = [
  { title: "Concept Explainer", desc: "Clear explanations with real-life examples for any topic." },
  { title: "Practice Questions", desc: "Adaptive quizzes that get harder as you improve." },
  { title: "Video RAG", desc: "Ask questions about any video with timestamp citations." },
  { title: "Progress Tracker", desc: "Mastery and weak spots tracked across every session." },
  { title: "Resource Finder", desc: "Curated extra resources when you need to go deeper." },
  { title: "Game Master", desc: "XP, streaks, badges, and boss-battle quiz challenges." },
  { title: "Code Reviewer", desc: "In-browser code, run it, get a real review for coding courses." },
];

export default function Features() {
  return (
    <section className="px-6 py-20 md:px-12">
      <h2 className="text-center font-display text-3xl font-bold md:text-4xl">Seven specialist agents, one tutor</h2>
      <div className="mx-auto mt-12 grid max-w-5xl grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-3">
        {FEATURES.map((f, i) => (
          <motion.div key={f.title}
            initial={{ opacity: 0, y: 20 }} whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }} transition={{ duration: 0.4, delay: i * 0.05 }}
            className="rounded-2xl border border-quest-muted/15 bg-quest-surface p-6 hover:border-quest-cyan/50">
            <h3 className="font-display text-lg font-semibold text-quest-cyan">{f.title}</h3>
            <p className="mt-2 text-sm text-quest-muted">{f.desc}</p>
          </motion.div>
        ))}
      </div>
    </section>
  );
}
```

- [ ] **Step 5: Create `frontend/components/landing/HowItWorks.tsx`**

```tsx
"use client";
import { motion } from "framer-motion";

const STEPS = [
  { n: "1", title: "Pick a course", desc: "Paste a YouTube playlist or choose a topic to learn." },
  { n: "2", title: "Follow the roadmap", desc: "Step through videos, quizzes, and code challenges." },
  { n: "3", title: "Level up", desc: "Earn XP, keep your streak, and master your weak spots." },
];

export default function HowItWorks() {
  return (
    <section id="how" className="px-6 py-20 md:px-12">
      <h2 className="text-center font-display text-3xl font-bold md:text-4xl">How it works</h2>
      <div className="mx-auto mt-12 grid max-w-4xl gap-6 md:grid-cols-3">
        {STEPS.map((s, i) => (
          <motion.div key={s.n}
            initial={{ opacity: 0, scale: 0.95 }} whileInView={{ opacity: 1, scale: 1 }}
            viewport={{ once: true }} transition={{ delay: i * 0.1 }}
            className="rounded-2xl bg-gradient-to-b from-quest-surface to-transparent p-6 text-center">
            <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-quest-violet font-display text-xl font-bold">{s.n}</div>
            <h3 className="mt-4 font-display text-lg font-semibold">{s.title}</h3>
            <p className="mt-2 text-sm text-quest-muted">{s.desc}</p>
          </motion.div>
        ))}
      </div>
    </section>
  );
}
```

- [ ] **Step 6: Create `frontend/components/landing/DemoPreview.tsx`**

```tsx
"use client";
import { motion } from "framer-motion";

export default function DemoPreview() {
  return (
    <section className="px-6 py-20 md:px-12">
      <div className="mx-auto max-w-4xl rounded-3xl border border-quest-muted/15 bg-quest-surface p-8">
        <h2 className="font-display text-2xl font-bold">Your roadmap, gamified</h2>
        <p className="mt-2 text-sm text-quest-muted">A preview of a course roadmap (interactive in later phases).</p>
        <div className="mt-6 space-y-3">
          {["Intro & setup", "Core concepts", "Hands-on project", "Final boss quiz"].map((step, i) => (
            <div key={step} className="flex items-center gap-3">
              <div className={`h-4 w-4 rounded-full ${i === 0 ? "bg-quest-lime" : "bg-quest-muted/30"}`} />
              <span className={i === 0 ? "text-quest-text" : "text-quest-muted"}>{step}</span>
            </div>
          ))}
        </div>
        <div className="mt-6 h-2 w-full overflow-hidden rounded-full bg-quest-bg">
          <motion.div initial={{ width: 0 }} whileInView={{ width: "25%" }} viewport={{ once: true }}
            transition={{ duration: 1 }} className="h-full bg-quest-lime" />
        </div>
        <p className="mt-2 text-xs text-quest-muted">25% complete · 1 of 4 steps</p>
      </div>
    </section>
  );
}
```

- [ ] **Step 7: Create `frontend/components/landing/Footer.tsx`**

```tsx
export default function Footer() {
  return (
    <footer className="border-t border-quest-muted/10 px-6 py-10 text-center text-sm text-quest-muted md:px-12">
      <p className="font-display text-quest-text">StudyQuest AI</p>
      <p className="mt-2">Learn anything. Level up. — Built as a multi-agent learning platform.</p>
    </footer>
  );
}
```

- [ ] **Step 8: Compose `frontend/app/page.tsx`**

```tsx
import Nav from "@/components/landing/Nav";
import Hero from "@/components/landing/Hero";
import Features from "@/components/landing/Features";
import HowItWorks from "@/components/landing/HowItWorks";
import DemoPreview from "@/components/landing/DemoPreview";
import Footer from "@/components/landing/Footer";

export default function Home() {
  return (
    <main>
      <Nav />
      <Hero />
      <Features />
      <HowItWorks />
      <DemoPreview />
      <Footer />
    </main>
  );
}
```

- [ ] **Step 9: Visual check**

Run (from `frontend/`): `npm run dev`
Expected: full animated landing page renders — hero reveal, glowing orb, feature cards animate on scroll, progress bar fills. No console errors.

- [ ] **Step 10: Commit**

```bash
git add frontend/components frontend/app/page.tsx
git commit -m "feat(frontend): build animated landing page"
```

---

### Task 9: Auth pages + protected dashboard

**Files:**
- Create: `frontend/components/ui/Input.tsx`
- Create: `frontend/app/signup/page.tsx`
- Create: `frontend/app/login/page.tsx`
- Create: `frontend/app/dashboard/page.tsx`

**Interfaces:**
- Consumes: `useAuth()`, `ApiError`, `Input`, `Button`, Next.js `useRouter`.
- Produces: working `/signup`, `/login` forms; protected `/dashboard`.

- [ ] **Step 1: Create `frontend/components/ui/Input.tsx`**

```tsx
export function Input(props: React.InputHTMLAttributes<HTMLInputElement> & { label: string }) {
  const { label, ...rest } = props;
  return (
    <label className="block">
      <span className="mb-1 block text-sm text-quest-muted">{label}</span>
      <input {...rest}
        className="w-full rounded-xl border border-quest-muted/30 bg-quest-bg px-4 py-3 text-quest-text outline-none focus:border-quest-cyan" />
    </label>
  );
}
```

- [ ] **Step 2: Create `frontend/app/signup/page.tsx`**

```tsx
"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth";
import { ApiError } from "@/lib/api";
import { Input } from "@/components/ui/Input";

export default function SignupPage() {
  const { signup } = useAuth();
  const router = useRouter();
  const [form, setForm] = useState({ email: "", password: "", display_name: "" });
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(""); setLoading(true);
    try {
      await signup(form.email, form.password, form.display_name);
      router.push("/dashboard");
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Something went wrong");
    } finally { setLoading(false); }
  }

  return (
    <main className="mx-auto flex min-h-screen max-w-md flex-col justify-center px-6">
      <h1 className="font-display text-3xl font-bold">Begin your quest</h1>
      <form onSubmit={onSubmit} className="mt-8 space-y-4">
        <Input label="Display name" required value={form.display_name}
          onChange={(e) => setForm({ ...form, display_name: e.target.value })} />
        <Input label="Email" type="email" required value={form.email}
          onChange={(e) => setForm({ ...form, email: e.target.value })} />
        <Input label="Password (min 8 chars)" type="password" required minLength={8} value={form.password}
          onChange={(e) => setForm({ ...form, password: e.target.value })} />
        {error && <p className="text-sm text-red-400">{error}</p>}
        <button type="submit" disabled={loading}
          className="w-full rounded-xl bg-quest-violet py-3 font-display font-medium disabled:opacity-50">
          {loading ? "Creating account..." : "Create account"}
        </button>
      </form>
      <p className="mt-4 text-sm text-quest-muted">Already have an account? <a href="/login" className="text-quest-cyan">Log in</a></p>
    </main>
  );
}
```

- [ ] **Step 3: Create `frontend/app/login/page.tsx`**

```tsx
"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth";
import { ApiError } from "@/lib/api";
import { Input } from "@/components/ui/Input";

export default function LoginPage() {
  const { login } = useAuth();
  const router = useRouter();
  const [form, setForm] = useState({ email: "", password: "" });
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(""); setLoading(true);
    try {
      await login(form.email, form.password);
      router.push("/dashboard");
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Something went wrong");
    } finally { setLoading(false); }
  }

  return (
    <main className="mx-auto flex min-h-screen max-w-md flex-col justify-center px-6">
      <h1 className="font-display text-3xl font-bold">Welcome back</h1>
      <form onSubmit={onSubmit} className="mt-8 space-y-4">
        <Input label="Email" type="email" required value={form.email}
          onChange={(e) => setForm({ ...form, email: e.target.value })} />
        <Input label="Password" type="password" required value={form.password}
          onChange={(e) => setForm({ ...form, password: e.target.value })} />
        {error && <p className="text-sm text-red-400">{error}</p>}
        <button type="submit" disabled={loading}
          className="w-full rounded-xl bg-quest-violet py-3 font-display font-medium disabled:opacity-50">
          {loading ? "Logging in..." : "Log in"}
        </button>
      </form>
      <p className="mt-4 text-sm text-quest-muted">New here? <a href="/signup" className="text-quest-cyan">Start your quest</a></p>
    </main>
  );
}
```

- [ ] **Step 4: Create `frontend/app/dashboard/page.tsx`**

```tsx
"use client";
import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth";

export default function Dashboard() {
  const { user, loading, logout } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!loading && !user) router.push("/login");
  }, [loading, user, router]);

  if (loading || !user) return <main className="p-10 text-quest-muted">Loading...</main>;

  return (
    <main className="mx-auto max-w-3xl px-6 py-16">
      <h1 className="font-display text-3xl font-bold">Welcome, {user.display_name} 👋</h1>
      <p className="mt-3 text-quest-muted">
        Your quest begins in Phase 2 — the AI tutor, roadmaps, and games are on the way.
      </p>
      <button onClick={logout} className="mt-8 rounded-xl border border-quest-muted/40 px-5 py-2 hover:border-quest-cyan">
        Log out
      </button>
    </main>
  );
}
```

- [ ] **Step 5: End-to-end manual verification**

With backend running (`uvicorn app.main:app --reload` from `backend/`) and frontend (`npm run dev`):
- Visit `/signup`, create an account → redirected to `/dashboard` showing the display name.
- Log out → redirected away; visiting `/dashboard` directly redirects to `/login`.
- Log in with the same credentials → back to `/dashboard`.
- Try signing up with the same email again → inline "Email already registered" error.
Expected: all four behaviors work.

- [ ] **Step 6: Commit**

```bash
git add frontend/app/signup frontend/app/login frontend/app/dashboard frontend/components/ui/Input.tsx
git commit -m "feat(frontend): add signup/login pages + protected dashboard"
```

---

### Task 10: Project glue — env examples, gitignore, docker-compose, README

**Files:**
- Create: `backend/.env.example`
- Create: `.gitignore`
- Create: `docker-compose.yml`
- Create: `README.md`

**Interfaces:**
- Produces: documented setup; optional Postgres compose; secrets ignored by git.

- [ ] **Step 1: Create `backend/.env.example`**

```
# --- Phase 1 (required to run) ---
DATABASE_URL=sqlite:///./studyquest.db
SECRET_KEY=change-me-to-a-long-random-string
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7
FRONTEND_ORIGIN=http://localhost:3000

# --- Later phases (placeholders; not needed for Phase 1) ---
# ANTHROPIC_API_KEY=          # Phase 2+: Claude API (pay-as-you-go)
# YOUTUBE_API_KEY=            # Phase 4: YouTube Data API
# LANGCHAIN_API_KEY=          # Phase 10: LangSmith tracing (optional)
# LANGCHAIN_TRACING_V2=true   # Phase 10: enable tracing
```

- [ ] **Step 2: Create root `.gitignore`**

```
# Python
__pycache__/
*.pyc
.venv/
backend/.venv/
*.db
.env
# Node / Next
node_modules/
.next/
# Env
.env.local
# OS
.DS_Store
```

- [ ] **Step 3: Create `docker-compose.yml` (optional, for when Postgres is wanted)**

```yaml
# Optional: Phase 1 runs natively with SQLite and does NOT need this.
# Use `docker compose up db` to get a Postgres for production-parity testing,
# then set DATABASE_URL=postgresql+psycopg://studyquest:studyquest@localhost:5432/studyquest
services:
  db:
    image: postgres:16
    environment:
      POSTGRES_USER: studyquest
      POSTGRES_PASSWORD: studyquest
      POSTGRES_DB: studyquest
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data
volumes:
  pgdata:
```

- [ ] **Step 4: Create `README.md`**

````markdown
# StudyQuest AI

A gamified, multi-agent AI tutoring platform. **Phase 1** delivers a running shell:
an animated landing page, custom-JWT auth, and a SQLite/Postgres-ready database.

## Architecture
- **Backend:** FastAPI + SQLAlchemy 2.0 + Alembic + Pydantic v2 (`backend/`).
- **Frontend:** Next.js 14 (App Router) + TypeScript + Tailwind + Framer Motion (`frontend/`).
- **DB:** SQLite for dev (zero install); set `DATABASE_URL` to a Postgres URL for prod — no code change.
- **Auth:** custom JWT (access + rotating, revocable refresh tokens).

Later phases add the LangGraph supervisor + specialist agents, CrewAI study-plan crew,
multimodal learning, YouTube roadmaps, code review, video RAG, gamification, dashboards,
guardrails, and LangSmith tracing. See `docs/superpowers/specs/`.

## Run it locally (no Docker, no paid keys)

### Backend
```bash
cd backend
python -m venv .venv
# Windows: . .venv/Scripts/activate   |   macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # Windows: copy .env.example .env
alembic upgrade head        # creates studyquest.db with users + refresh_tokens
uvicorn app.main:app --reload   # http://localhost:8000  (docs at /docs)
```

### Frontend
```bash
cd frontend
npm install
cp .env.local.example .env.local   # Windows: copy .env.local.example .env.local
npm run dev                          # http://localhost:3000
```

Open http://localhost:3000 → sign up → land on the dashboard. The full auth round-trip
(signup → login → protected dashboard → logout) works end to end.

## Tests
```bash
cd backend && pytest -v
```

## Using Postgres instead of SQLite (optional)
```bash
docker compose up -d db
# set in backend/.env:
# DATABASE_URL=postgresql+psycopg://studyquest:studyquest@localhost:5432/studyquest
cd backend && alembic upgrade head
```
````

- [ ] **Step 5: Commit**

```bash
git add .gitignore docker-compose.yml README.md backend/.env.example
git commit -m "chore: add env examples, gitignore, docker-compose, README"
```

---

## Self-Review Notes
- **Spec coverage:** landing page (Task 8), auth (Tasks 3–5, 9), DB schema (Task 2), `.env.example` (Task 10), docker-compose (Task 10), error handling (`{detail,code}` in Tasks 1/5, `ApiError` in Task 7), testing (Tasks 1–5), native-run README (Task 10), guardrails/LangSmith documented as env placeholders (Task 10) + spec — all covered.
- **Type consistency:** `AuthResponse`/`TokenPair`/`UserOut` names match across backend (Task 4) and frontend (Task 7); `apiFetch`, `useAuth`, `ApiError` names consistent across Tasks 7–9.
- **Placeholders:** none — every code step contains complete content.
```
