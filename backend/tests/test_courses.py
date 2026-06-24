"""Phase 4 tests — exercise roadmap logic + per-step actions WITHOUT network by
seeding a course directly and stubbing transcript fetches."""
import app.api.routes.courses as courses_route
from app.agents import course_agent
from app.database import Base, SessionLocal, engine
from app.models.course import Course, CourseStep
from app.youtube import format_duration
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def setup_module():
    Base.metadata.create_all(bind=engine)


def test_format_duration():
    assert format_duration(45) == "45s"
    assert format_duration(95) == "1m 35s"
    assert format_duration(3725) == "1h 2m"


def test_estimate_adds_quiz_buffer():
    assert course_agent.estimate_step_seconds(600) == 600 + 300


def _token(email):
    return client.post("/api/auth/signup", json={
        "email": email, "password": "supersecret", "display_name": "C"}).json()["access_token"]


def _seed_course(user_email="course@x.com"):
    """Create a 2-step course directly (bypassing YouTube network)."""
    token = _token(user_email)
    # find the user id via /me
    me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"}).json()
    db = SessionLocal()
    c = Course(user_id=me["id"], title="Test Course", playlist_url="https://x/list=1",
               total_seconds=1200)
    db.add(c); db.flush()
    db.add(CourseStep(course_id=c.id, ordinal=0, video_id="vid0", title="Intro", duration_seconds=600))
    db.add(CourseStep(course_id=c.id, ordinal=1, video_id="vid1", title="Core", duration_seconds=600))
    db.commit()
    cid = c.id
    db.close()
    return token, cid


def test_get_course_roadmap_and_progress():
    token, cid = _seed_course("course1@x.com")
    h = {"Authorization": f"Bearer {token}"}
    r = client.get(f"/api/courses/{cid}", headers=h)
    assert r.status_code == 200
    body = r.json()
    assert body["total_steps"] == 2 and body["percent"] == 0
    assert body["steps"][0]["estimated"] == "15m 0s"


def test_complete_step_updates_percent_and_proficiency():
    token, cid = _seed_course("course2@x.com")
    h = {"Authorization": f"Bearer {token}"}
    steps = client.get(f"/api/courses/{cid}", headers=h).json()["steps"]
    r = client.post(f"/api/courses/{cid}/steps/{steps[0]['id']}/complete", headers=h)
    assert r.json()["percent"] == 50
    assert r.json()["proficient"] is False


def test_create_course_rejects_non_playlist_link():
    h = {"Authorization": f"Bearer {_token('badlink@x.com')}"}
    r = client.post("/api/courses", headers=h, json={"playlist_url": "https://youtu.be/single"})
    assert r.status_code == 400


def test_quiz_grade_marks_passed(monkeypatch):
    token, cid = _seed_course("course3@x.com")
    h = {"Authorization": f"Bearer {token}"}
    step_id = client.get(f"/api/courses/{cid}", headers=h).json()["steps"][0]["id"]
    # Avoid network: stub transcript fetch used inside the route.
    monkeypatch.setattr(courses_route, "fetch_transcript", lambda vid: [])
    graded = client.post(f"/api/courses/{cid}/steps/{step_id}/quiz/grade", headers=h,
                         json={"question": "main idea?", "selected": "The key concept it taught"})
    assert graded.status_code == 200
    assert "correct" in graded.json()
