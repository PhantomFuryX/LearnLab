import sys, os
from fastapi.testclient import TestClient
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from backend.main import app

client = TestClient(app)


def test_ingest_fetch_headers_and_trafilatura(monkeypatch):
    # Monkeypatch WebFetchTool.run to capture headers and return simple HTML
    calls = {}
    def fake_run(self, url, headers=None, respect_robots=True, delay_ms=0, **kwargs):
        calls['headers'] = headers
        return {"url": url, "status": 200, "headers": {"Content-Type": "text/html"}, "text": "<html><body>Hello</body></html>"}

    # Monkeypatch trafilatura.extract to return content
    class FakeTraf:
        @staticmethod
        def extract(html):
            return "EXTRACTED"
    import backend.routers.knowledge as knowledge_mod
    monkeypatch.setattr(knowledge_mod, 'trafilatura', FakeTraf, raising=False)
    monkeypatch.setattr(knowledge_mod, 'HAS_TRAF', True, raising=False)

    from backend.core.tools.web_fetch import WebFetchTool
    monkeypatch.setattr(WebFetchTool, 'run', fake_run, raising=True)

    payload = {
        "namespace": "fetch-ns",
        "urls": ["https://example.test"],
        "headers": {"Accept-Language": "en-US"},
        "respect_robots": True,
        "delay_ms": 0,
        "chunk_size": 64,
        "chunk_overlap": 8
    }
    r = client.post("/knowledge/ingest_fetch", json=payload)
    assert r.status_code == 200
    data = r.json()
    assert data["namespace"] == "fetch-ns"
    assert data["count"] >= 1
    assert calls["headers"]["Accept-Language"] == "en-US"


def test_ingest_fetch_robots_disallow(monkeypatch):
    # Simulate robots disallow by returning error from tool
    def fake_run(self, url, headers=None, respect_robots=True, delay_ms=0, **kwargs):
        return {"error": "Disallowed by robots.txt", "url": url}

    import backend.routers.knowledge as knowledge_mod
    monkeypatch.setattr(knowledge_mod, 'HAS_TRAF', False, raising=False)
    monkeypatch.setattr(knowledge_mod, 'HAS_BS4', False, raising=False)

    from backend.core.tools.web_fetch import WebFetchTool
    monkeypatch.setattr(WebFetchTool, 'run', fake_run, raising=True)

    payload = {
        "namespace": "fetch-ns2",
        "urls": ["https://blocked.example"],
        "respect_robots": True
    }
    r = client.post("/knowledge/ingest_fetch", json=payload)
    assert r.status_code == 200
    data = r.json()
    assert data["count"] == 0


def test_chat_ask_stream_sse(monkeypatch):
    # Ensure /chat/ask_stream streams SSE using orchestrator.stream
    from backend.core.orchestrator import Orchestrator
    async def fake_stream(self, payload):
        yield "event: step\ndata: {\"name\":\"router\"}\n\n"
        yield "event: token\ndata: part1\n\n"
        yield "event: token\ndata: part2\n\n"
        yield "event: done\ndata: \n\n"
    monkeypatch.setattr(Orchestrator, 'stream', fake_stream)

    with client.stream("POST", "/chat/ask_stream", json={"prompt": "hi"}) as r:
        chunks = list(r.iter_text())
        text = "".join(chunks)
        assert r.status_code == 200
        assert "event: step" in text
        assert "event: token" in text
        assert text.strip().endswith("event: done\ndata:")
