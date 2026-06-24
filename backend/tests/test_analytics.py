"""Phase 9 tests — student analytics + teacher gating."""
from fastapi.testclient import TestClient

from app.database import Base, engine
from app.main import app

client = TestClient(app)


def setup_module():
    Base.metadata.create_all(bind=engine)


def _signup(email, role="student"):
    return client.post("/api/auth/signup", json={
        "email": email, "password": "supersecret", "display_name": email.split("@")[0], "role": role
    }).json()["access_token"]


def test_my_analytics_shape():
    h = {"Authorization": f"Bearer {_signup('stud@x.com')}"}
    r = client.get("/api/analytics/me", headers=h)
    assert r.status_code == 200
    body = r.json()
    for key in ("xp", "level", "streak", "courses", "weak_spots", "quizzes_passed"):
        assert key in body


def test_students_overview_requires_teacher():
    student = {"Authorization": f"Bearer {_signup('s2@x.com')}"}
    assert client.get("/api/analytics/students", headers=student).status_code == 403

    teacher = {"Authorization": f"Bearer {_signup('teacher@x.com', role='teacher')}"}
    r = client.get("/api/analytics/students", headers=teacher)
    assert r.status_code == 200
    assert isinstance(r.json(), list)
