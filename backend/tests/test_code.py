"""Phase 5 tests — real sandbox execution + review gating (mock LLM)."""
from fastapi.testclient import TestClient

from app.database import Base, engine
from app.main import app
from app.sandbox import run_code

client = TestClient(app)


def setup_module():
    Base.metadata.create_all(bind=engine)


def test_sandbox_runs_python():
    r = run_code("python", "print(6 * 7)")
    assert r["ok"] is True and r["stdout"].strip() == "42"


def test_sandbox_captures_error():
    r = run_code("python", "raise ValueError('boom')")
    assert r["ok"] is False and "ValueError" in r["stderr"]


def test_sandbox_times_out():
    r = run_code("python", "while True:\n    pass")
    assert r["timed_out"] is True and r["ok"] is False


def test_sandbox_rejects_unsupported_language():
    r = run_code("ruby", "puts 1")
    assert r["ok"] is False and "Unsupported" in r["stderr"]


def _token(email):
    return client.post("/api/auth/signup", json={
        "email": email, "password": "supersecret", "display_name": "K"}).json()["access_token"]


def test_run_endpoint_requires_auth_and_runs():
    assert client.post("/api/code/run", json={"language": "python", "code": "print(1)"}).status_code == 401
    h = {"Authorization": f"Bearer {_token('coder@x.com')}"}
    r = client.post("/api/code/run", headers=h, json={"language": "python", "code": "print('hi')"})
    assert r.status_code == 200 and r.json()["stdout"].strip() == "hi"


def test_review_endpoint_returns_verdict():
    h = {"Authorization": f"Bearer {_token('rev@x.com')}"}
    r = client.post("/api/code/review", headers=h,
                    json={"language": "python", "code": "print(2+2)", "task": "print 4"})
    body = r.json()
    assert "approved" in body and "review" in body and "run" in body
    assert body["run"]["ok"] is True
