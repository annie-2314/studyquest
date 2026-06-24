"""Phase 6 tests — windowing + video Q&A using injected segments (no network)."""
from fastapi.testclient import TestClient

from app.database import Base, SessionLocal, engine
from app.main import app
from app.rag import store
from app.transcribe import youtube_video_id

client = TestClient(app)


def setup_module():
    Base.metadata.create_all(bind=engine)


def test_youtube_id_parsing():
    assert youtube_video_id("https://youtu.be/abc123XYZ_-") == "abc123XYZ_-"
    assert youtube_video_id("https://www.youtube.com/watch?v=dQw4w9WgXcQ") == "dQw4w9WgXcQ"
    assert youtube_video_id("not a url") is None


def test_segments_document_windows_with_timestamps():
    db = SessionLocal()
    segments = [{"text": f"sentence {i}", "start": i * 5, "duration": 5} for i in range(20)]
    doc = store.add_segments_document(db, "vu1", "Test Video", segments)
    assert len(doc.chunks) >= 2
    # First chunk cited at 00:00.
    assert doc.chunks[0].source_ref == "00:00"
    db.close()


def _token(email):
    return client.post("/api/auth/signup", json={
        "email": email, "password": "supersecret", "display_name": "V"}).json()["access_token"]


def test_ask_video_with_seeded_transcript():
    token = _token("video@x.com")
    me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"}).json()
    db = SessionLocal()
    segments = [{"text": "Gravity pulls objects toward Earth.", "start": 0, "duration": 5},
                {"text": "Acceleration is 9.8 meters per second squared.", "start": 30, "duration": 5}]
    doc = store.add_segments_document(db, me["id"], "Physics", segments)
    doc_id = doc.id
    db.close()

    h = {"Authorization": f"Bearer {token}"}
    r = client.post(f"/api/video/{doc_id}/ask", headers=h, json={"question": "what is acceleration?"})
    assert r.status_code == 200
    assert len(r.json()["citations"]) >= 1


def test_ask_missing_video_404():
    h = {"Authorization": f"Bearer {_token('novid@x.com')}"}
    assert client.post("/api/video/nope/ask", headers=h, json={"question": "x"}).status_code == 404
