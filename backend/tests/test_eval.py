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
