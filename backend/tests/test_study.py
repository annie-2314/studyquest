"""Phase 3 tests — RAG + image solve in mock mode."""
import io

from fastapi.testclient import TestClient

from app.database import Base, engine
from app.main import app
from app.rag import store

client = TestClient(app)


def setup_module():
    Base.metadata.create_all(bind=engine)


def _token(email):
    return client.post("/api/auth/signup", json={
        "email": email, "password": "supersecret", "display_name": "S"}).json()["access_token"]


def test_chunking_splits_long_text():
    chunks = store.chunk_text("para one.\n\n" + ("x" * 1300))
    assert len(chunks) >= 2


def test_document_add_and_ask_with_citations():
    h = {"Authorization": f"Bearer {_token('rag@x.com')}"}
    doc = client.post("/api/study/documents", headers=h, json={
        "title": "Photosynthesis",
        "text": "Photosynthesis is how plants make food from sunlight.\n\n"
                "Chlorophyll absorbs light. Water and CO2 become glucose and oxygen."})
    assert doc.status_code == 201 and doc.json()["chunks"] >= 1

    ans = client.post("/api/study/ask", headers=h, json={"query": "how do plants make food?"})
    assert ans.status_code == 200
    body = ans.json()
    assert "answer" in body and len(body["citations"]) >= 1


def test_ask_empty_knowledge_base():
    h = {"Authorization": f"Bearer {_token('empty@x.com')}"}
    ans = client.post("/api/study/ask", headers=h, json={"query": "anything"})
    assert ans.status_code == 200
    assert ans.json()["citations"] == []


def test_solve_image_accepts_image_and_rejects_nonimage():
    h = {"Authorization": f"Bearer {_token('img@x.com')}"}
    img = client.post("/api/study/solve-image", headers=h,
                      files={"file": ("p.png", io.BytesIO(b"\x89PNG\r\n\x1a\n"), "image/png")},
                      data={"question": "solve this"})
    assert img.status_code == 200 and "answer" in img.json()

    bad = client.post("/api/study/solve-image", headers=h,
                      files={"file": ("p.txt", io.BytesIO(b"hello"), "text/plain")})
    assert bad.status_code == 400
