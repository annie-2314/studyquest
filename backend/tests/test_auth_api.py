import pytest
from fastapi.testclient import TestClient

from app.database import Base, engine
from app.main import app

client = TestClient(app)


def setup_module():
    Base.metadata.create_all(bind=engine)


def _signup(email="u1@x.com"):
    return client.post("/api/auth/signup", json={
        "email": email, "password": "supersecret", "display_name": "U1"})


def test_signup_returns_tokens_and_user():
    r = _signup("new@x.com")
    assert r.status_code == 201
    body = r.json()
    assert body["access_token"] and body["refresh_token"]
    assert body["user"]["email"] == "new@x.com"


def test_duplicate_email_conflict():
    _signup("dup@x.com")
    r = _signup("dup@x.com")
    assert r.status_code == 409
    assert r.json()["code"] == "http_409"


def test_login_success_and_wrong_password():
    _signup("login@x.com")
    ok = client.post("/api/auth/login", json={"email": "login@x.com", "password": "supersecret"})
    assert ok.status_code == 200 and ok.json()["access_token"]
    bad = client.post("/api/auth/login", json={"email": "login@x.com", "password": "nope12345"})
    assert bad.status_code == 401


def test_me_requires_token():
    assert client.get("/api/auth/me").status_code == 401
    token = _signup("me@x.com").json()["access_token"]
    r = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200 and r.json()["email"] == "me@x.com"


def test_refresh_and_logout():
    rt = _signup("ref@x.com").json()["refresh_token"]
    refreshed = client.post("/api/auth/refresh", json={"refresh_token": rt})
    assert refreshed.status_code == 200 and refreshed.json()["access_token"]
    out = client.post("/api/auth/logout", json={"refresh_token": rt})
    assert out.status_code == 200
    # revoked token can no longer refresh
    assert client.post("/api/auth/refresh", json={"refresh_token": rt}).status_code == 401
