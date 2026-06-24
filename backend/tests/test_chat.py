"""Phase 2 tests — run in mock LLM mode (no key needed)."""
import asyncio

from fastapi.testclient import TestClient

from app.agents import supervisor
from app.database import Base, engine
from app.main import app

client = TestClient(app)


def setup_module():
    Base.metadata.create_all(bind=engine)


def test_routing_classifies_intents():
    assert supervisor.classify_route("Can you quiz me on photosynthesis?") == "practice_question"
    assert supervisor.classify_route("how am i doing so far?") == "progress_tracker"
    assert supervisor.classify_route("explain recursion") == "concept_explainer"


def test_run_turn_returns_answer_via_graph():
    out = supervisor.run_turn("u1", [], "explain recursion", "No prior profile.")
    assert out["route"] == "concept_explainer"
    assert isinstance(out["answer"], str) and len(out["answer"]) > 0


def test_stream_turn_yields_route_then_tokens():
    async def collect():
        kinds = []
        async for kind, _ in supervisor.stream_turn("u1", [], "explain loops", "none"):
            kinds.append(kind)
        return kinds
    kinds = asyncio.run(collect())
    assert kinds[0] == "route"
    assert "token" in kinds[1:]


def _auth_token():
    r = client.post("/api/auth/signup", json={
        "email": "chat@x.com", "password": "supersecret", "display_name": "Chat"})
    return r.json()["access_token"]


def test_conversation_crud_requires_auth():
    assert client.get("/api/chat/conversations").status_code == 401
    token = _auth_token()
    h = {"Authorization": f"Bearer {token}"}
    created = client.post("/api/chat/conversations", headers=h)
    assert created.status_code == 201
    conv_id = created.json()["id"]
    assert client.get("/api/chat/conversations", headers=h).status_code == 200
    msgs = client.get(f"/api/chat/conversations/{conv_id}/messages", headers=h)
    assert msgs.status_code == 200 and msgs.json() == []


def test_ws_streams_and_persists():
    token = _auth_token_unique("ws@x.com")
    with client.websocket_connect("/api/chat/ws") as ws:
        ws.send_json({"token": token, "message": "explain gravity"})
        saw_route = saw_token = saw_done = False
        conv_id = None
        while True:
            msg = ws.receive_json()
            if msg["type"] == "route":
                saw_route = True
            elif msg["type"] == "token":
                saw_token = True
            elif msg["type"] == "done":
                saw_done = True
                conv_id = msg["conversation_id"]
                break
        assert saw_route and saw_token and saw_done and conv_id


def _auth_token_unique(email: str):
    r = client.post("/api/auth/signup", json={
        "email": email, "password": "supersecret", "display_name": "WS"})
    return r.json()["access_token"]
