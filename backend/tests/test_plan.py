"""Phase 8 tests — crew study plan + PDF export (mock LLM)."""
from fastapi.testclient import TestClient

from app.crew.study_plan import run_study_plan_crew
from app.database import Base, engine
from app.main import app
from app.pdf import build_study_guide_pdf

client = TestClient(app)


def setup_module():
    Base.metadata.create_all(bind=engine)


def test_crew_produces_structured_plan():
    plan = run_study_plan_crew("photosynthesis", weak_spots=["chlorophyll"])
    assert plan["topic"] == "photosynthesis"
    assert len(plan["modules"]) >= 1
    assert "practice_questions" in plan["modules"][0]
    assert plan["review_notes"]


def test_pdf_bytes_are_a_pdf():
    plan = run_study_plan_crew("algebra")
    data = build_study_guide_pdf(plan)
    assert isinstance(data, (bytes, bytearray)) and data[:4] == b"%PDF"


def _token(email):
    return client.post("/api/auth/signup", json={
        "email": email, "password": "supersecret", "display_name": "P"}).json()["access_token"]


def test_plan_endpoint_and_pdf_download():
    h = {"Authorization": f"Bearer {_token('plan@x.com')}"}
    p = client.post("/api/plan", headers=h, json={"topic": "calculus"})
    assert p.status_code == 200
    body = p.json()
    assert body["topic"] == "calculus" and body["modules"]

    pdf = client.post("/api/plan/pdf", headers=h, json=body)
    assert pdf.status_code == 200
    assert pdf.headers["content-type"] == "application/pdf"
    assert pdf.content[:4] == b"%PDF"
