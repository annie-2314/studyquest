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
