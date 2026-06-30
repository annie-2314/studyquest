"""Phase 8 tests — roadmap crew + PDF export (mock LLM)."""
from fastapi.testclient import TestClient

from app.crew.roadmap import run_roadmap_crew, youtube_search_url
from app.database import Base, engine
from app.main import app
from app.pdf import build_roadmap_pdf

client = TestClient(app)


def setup_module():
    Base.metadata.create_all(bind=engine)


def test_youtube_search_url_encodes_query():
    url = youtube_search_url("python full course")
    assert url.startswith("https://www.youtube.com/results?search_query=")
    assert "python+full+course" in url


def test_crew_produces_time_boxed_phases_with_resources():
    rm = run_roadmap_crew("photosynthesis", hours_per_week=4, timeline="4 weeks",
                          language="English", weak_spots=["chlorophyll"])
    assert rm["goal"] == "photosynthesis"
    assert len(rm["phases"]) >= 1
    first = rm["phases"][0]
    assert first["topics"] and first["resources"]
    assert first["resources"][0]["url"].startswith("https://www.youtube.com/")
    assert rm["review_notes"]


def test_roadmap_pdf_bytes_are_a_pdf():
    rm = run_roadmap_crew("algebra")
    data = build_roadmap_pdf(rm)
    assert isinstance(data, (bytes, bytearray)) and data[:4] == b"%PDF"


def _token(email):
    return client.post("/api/auth/signup", json={
        "email": email, "password": "supersecret", "display_name": "P"}).json()["access_token"]


def test_plan_endpoint_and_pdf_download():
    h = {"Authorization": f"Bearer {_token('plan@x.com')}"}
    p = client.post("/api/plan", headers=h, json={
        "goal": "agentic AI", "hours_per_week": 6, "timeline": "8 weeks", "language": "Python"})
    assert p.status_code == 200
    body = p.json()
    assert body["goal"] == "agentic AI" and body["phases"]

    pdf = client.post("/api/plan/pdf", headers=h, json=body)
    assert pdf.status_code == 200
    assert pdf.headers["content-type"] == "application/pdf"
    assert pdf.content[:4] == b"%PDF"


def test_roadmaps_are_saved_listed_and_deletable():
    h = {"Authorization": f"Bearer {_token('rmsave@x.com')}"}
    made = client.post("/api/plan", headers=h, json={"goal": "calculus"}).json()
    rid = made["id"]
    assert rid

    lst = client.get("/api/plan/list", headers=h)
    assert lst.status_code == 200 and any(r["id"] == rid for r in lst.json())

    got = client.get(f"/api/plan/{rid}", headers=h)
    assert got.status_code == 200 and got.json()["goal"] == "calculus" and got.json()["phases"]

    dele = client.delete(f"/api/plan/{rid}", headers=h)
    assert dele.status_code == 204
    assert client.get(f"/api/plan/{rid}", headers=h).status_code == 404
