import sys, os, asyncio
from fastapi.testclient import TestClient
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from backend.main import app
from backend.core.orchestrator import Orchestrator

client = TestClient(app)


def test_agents_run_success(monkeypatch):
    async def fake_run(self, payload):
        return {"result": "ok", "steps": [{"name": "router", "detail": "route=knowledge"}]}
    monkeypatch.setattr(Orchestrator, "run", fake_run)

    r = client.post("/agents/run", json={"session_id": "s", "message": "hi"})
    assert r.status_code == 200
    body = r.json()
    assert body["final"] == "ok"
    assert body["steps"][0]["name"] == "router"


def test_agents_run_error(monkeypatch):
    async def boom(self, payload):
        raise RuntimeError("fail")
    monkeypatch.setattr(Orchestrator, "run", boom)
    r = client.post("/agents/run", json={"session_id": "s", "message": "hi"})
    assert r.status_code == 500


def test_agents_stream_sse(monkeypatch):
    async def fake_stream(self, payload):
        yield "event: step\ndata: {\"name\":\"router\"}\n\n"
        yield "event: token\ndata: hello \n\n"
        yield "event: token\ndata: world\n\n"
        yield "event: done\ndata: \n\n"
    monkeypatch.setattr(Orchestrator, "stream", fake_stream)

    with client.stream("POST", "/agents/stream", json={"session_id": "s", "message": "hi"}) as r:
        # Read response to ensure streaming content is consumed
        chunks = list(r.iter_text())
        text = "".join(chunks)
        assert r.status_code == 200
        assert "event: step" in text
        assert "token" in text
        assert "done" in text
