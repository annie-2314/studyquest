"""Phase 10 tests — eval harness + observability status (mock mode)."""
from fastapi.testclient import TestClient

from app.database import Base, engine
from app.eval import harness
from app.main import app
from app.observability import init_tracing

client = TestClient(app)


def setup_module():
    Base.metadata.create_all(bind=engine)


def test_judge_returns_score_in_range():
    v = harness.judge_explanation("Explain loops", "A loop repeats code. For example, counting to 10.")
    assert 1 <= v["score"] <= 5 and v["rationale"]


def test_run_explanation_eval_aggregates():
    report = harness.run_explanation_eval(["Explain recursion."])
    assert report["n"] == 1 and 1 <= report["average_score"] <= 5


def test_tracing_off_by_default():
    status = init_tracing()
    assert status["tracing"] is False


def _token(email):
    return client.post("/api/auth/signup", json={
        "email": email, "password": "supersecret", "display_name": "E"}).json()["access_token"]


def test_eval_endpoints():
    h = {"Authorization": f"Bearer {_token('eval@x.com')}"}
    j = client.post("/api/eval/explanation", headers=h,
                    json={"question": "what is x", "answer": "x is a variable, for example age=5."})
    assert j.status_code == 200 and 1 <= j.json()["score"] <= 5

    qi = client.get("/api/eval/quiz-improvement", headers=h)
    assert qi.status_code == 200 and "enough_data" in qi.json()

    obs = client.get("/api/eval/obs-status", headers=h)
    assert obs.status_code == 200 and "tracing" in obs.json()

    # Traces endpoint: tracing is off in tests, so it returns a clean empty set.
    tr = client.get("/api/eval/traces", headers=h)
    assert tr.status_code == 200
    assert tr.json()["enabled"] is False and tr.json()["runs"] == []


def test_factuality_grounded_vs_hallucinated_and_persisted():
    h = {"Authorization": f"Bearer {_token('fact@x.com')}"}
    sources = ["Photosynthesis happens in the chloroplasts of plant cells."]

    grounded = client.post("/api/eval/factuality", headers=h, json={
        "answer": "Photosynthesis occurs in chloroplasts.", "sources": sources})
    assert grounded.status_code == 200 and grounded.json()["grounded"] is True

    hallu = client.post("/api/eval/factuality", headers=h, json={
        "answer": "Photosynthesis occurs on the moon made of cheese.", "sources": sources})
    assert hallu.status_code == 200 and hallu.json()["grounded"] is False

    # Both runs are persisted and surfaced by the report endpoint.
    res = client.get("/api/eval/results", headers=h)
    assert res.status_code == 200 and len([r for r in res.json() if r["kind"] == "factuality"]) >= 2


def test_quiz_validity_endpoint():
    h = {"Authorization": f"Bearer {_token('qv@x.com')}"}
    r = client.post("/api/eval/quiz-validity", headers=h, json={
        "question": "What is 2 + 2?", "options": ["4", "5", "6", "7"], "answer_index": 0})
    assert r.status_code == 200 and r.json()["valid"] is True
