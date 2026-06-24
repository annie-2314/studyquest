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
