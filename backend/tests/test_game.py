"""Phase 7 tests — XP/levels/streaks/badges/leaderboard + mini-games (mock)."""
from fastapi.testclient import TestClient

from app.database import Base, SessionLocal, engine
from app.gamification import service
from app.main import app

client = TestClient(app)


def setup_module():
    Base.metadata.create_all(bind=engine)


def test_level_math():
    assert service.level_for_xp(0) == 1
    assert service.level_for_xp(150) == 2
    assert service.xp_into_level(150) == 50


def test_award_xp_and_threshold_badge():
    db = SessionLocal()
    out = service.award_xp(db, "gp_user_1", 120, reason="test")
    assert out["xp"] == 120 and out["level"] == 2
    keys = {b["key"] for b in out["badges"] if b["earned"]}
    assert "first_xp" in keys and "centurion" in keys
    assert out["streak"] == 1  # first activity starts a streak
    db.close()


def test_token_and_profile_endpoint():
    token = client.post("/api/auth/signup", json={
        "email": "game@x.com", "password": "supersecret", "display_name": "Gamer"}).json()["access_token"]
    h = {"Authorization": f"Bearer {token}"}
    p = client.get("/api/game/profile", headers=h)
    assert p.status_code == 200 and p.json()["level"] == 1

    xp = client.post("/api/game/xp", headers=h, json={"amount": 999, "reason": "win"})
    assert xp.json()["xp"] == 50  # capped at 50 per call

    lb = client.get("/api/game/leaderboard", headers=h)
    assert lb.status_code == 200 and any(r["display_name"] == "Gamer" for r in lb.json())


def test_minigames_return_content():
    h = {"Authorization": f"Bearer " + client.post("/api/auth/signup", json={
        "email": "mg@x.com", "password": "supersecret", "display_name": "MG"}).json()["access_token"]}
    fc = client.post("/api/game/flashcards", headers=h, json={"topic": "fractions"})
    assert fc.status_code == 200 and len(fc.json()["cards"]) >= 1
    boss = client.post("/api/game/boss", headers=h, json={"topic": "fractions"})
    assert boss.status_code == 200 and len(boss.json()["questions"]) >= 1
    assert "answer_index" in boss.json()["questions"][0]


def test_summarize_returns_text():
    h = {"Authorization": f"Bearer " + client.post("/api/auth/signup", json={
        "email": "sum@x.com", "password": "supersecret", "display_name": "SUM"}).json()["access_token"]}
    r = client.post("/api/game/summarize", headers=h, json={"topic": "photosynthesis"})
    assert r.status_code == 200
    assert isinstance(r.json()["summary"], str) and r.json()["summary"].strip()


def test_explain_returns_text():
    h = {"Authorization": f"Bearer " + client.post("/api/auth/signup", json={
        "email": "ex@x.com", "password": "supersecret", "display_name": "EX"}).json()["access_token"]}
    r = client.post("/api/game/explain", headers=h, json={
        "topic": "fractions", "concept": "What is a fraction?",
        "correct_answer": "part of a whole", "interest": "football"})
    assert r.status_code == 200
    assert isinstance(r.json()["explanation"], str) and r.json()["explanation"].strip()
