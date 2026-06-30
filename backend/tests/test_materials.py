"""Grounded-RAG tests: ingest → cited retrieval, the not-found guard, and the
mastery endpoints. Runs with EMBEDDINGS_MOCK=1 (set in conftest) so no model
download is needed."""
from fastapi.testclient import TestClient

from app.database import Base, engine
from app.main import app

client = TestClient(app)


def setup_module():
    Base.metadata.create_all(bind=engine)


def _token(email):
    return client.post("/api/auth/signup", json={
        "email": email, "password": "supersecret", "display_name": "M"}).json()["access_token"]


def test_ingest_then_grounded_answer_with_citation():
    h = {"Authorization": f"Bearer {_token('mat@x.com')}"}
    ing = client.post("/api/materials/ingest/text", headers=h, json={
        "title": "Bio Notes",
        "text": ("Photosynthesis happens in the chloroplasts of plant cells. "
                 "Chlorophyll absorbs light. The Calvin cycle fixes carbon dioxide into glucose."),
    })
    assert ing.status_code == 201 and ing.json()["chunks"] >= 1

    lst = client.get("/api/materials", headers=h)
    assert lst.status_code == 200 and any(m["title"] == "Bio Notes" for m in lst.json())

    # A query that overlaps the source → grounded answer with at least one citation.
    ans = client.post("/api/materials/ask", headers=h,
                      json={"question": "photosynthesis chloroplasts chlorophyll"})
    assert ans.status_code == 200
    body = ans.json()
    assert body["grounded"] is True
    assert len(body["citations"]) >= 1
    assert "Bio Notes" in body["citations"][0]["ref"]


def test_not_found_when_query_unrelated():
    h = {"Authorization": f"Bearer {_token('mat2@x.com')}"}
    client.post("/api/materials/ingest/text", headers=h, json={
        "title": "Bio Notes", "text": "Photosynthesis happens in chloroplasts."})
    ans = client.post("/api/materials/ask", headers=h,
                      json={"question": "quantum cricket spaceship economics"})
    assert ans.status_code == 200
    body = ans.json()
    assert body["grounded"] is False
    assert body["citations"] == []


def test_mastery_endpoints_update_and_report():
    h = {"Authorization": f"Bearer {_token('mas@x.com')}"}
    # Record a couple of attempts, then mastery should reflect the concept.
    client.post("/api/learning/attempt", headers=h, json={"concept": "Fractions", "correct": True})
    r = client.post("/api/learning/attempt", headers=h, json={"concept": "Fractions", "correct": True})
    assert r.status_code == 200 and r.json()["concept"] == "fractions"

    m = client.get("/api/learning/mastery", headers=h)
    assert m.status_code == 200
    concepts = {c["concept"]: c for c in m.json()["concepts"]}
    assert "fractions" in concepts and concepts["fractions"]["attempts"] == 2
    assert len(m.json()["history"]) >= 2

    rq = client.get("/api/learning/review-queue", headers=h)
    assert rq.status_code == 200 and any(c["concept"] == "fractions" for c in rq.json())
