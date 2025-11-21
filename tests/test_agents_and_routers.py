import sys
import os
import pytest
from fastapi.testclient import TestClient

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend.main import app
from backend.core.agents.automation_agent import AutomationAgent
from backend.core.agents.integration_agent import IntegrationAgent

client = TestClient(app)

# ---------------- Agents unit tests -----------------

def test_automation_agent_success():
    agent = AutomationAgent()
    res = agent.handle({"task": "do"})
    assert res["result"].startswith("AutomationAgent handled")
    assert res["payload"]["task"] == "do"


def test_automation_agent_error():
    agent = AutomationAgent()
    with pytest.raises(ValueError):
        agent.handle({"raise": True})


def test_integration_agent_success():
    agent = IntegrationAgent()
    res = agent.handle({"action": "send"})
    assert res["result"].startswith("IntegrationAgent handled")
    assert res["payload"]["action"] == "send"


def test_integration_agent_error():
    agent = IntegrationAgent()
    with pytest.raises(ValueError):
        agent.handle({"raise": True})

# ---------------- Routers endpoint tests -----------------

def test_automation_router_success(monkeypatch):
    def fake_handle(self, payload):
        return {"ok": True}
    monkeypatch.setattr(AutomationAgent, "handle", fake_handle)

    r = client.post("/automate/run", json={"payload": {"x": 1}})
    assert r.status_code == 200
    assert r.json()["result"]["ok"] is True


def test_automation_router_error(monkeypatch):
    def fake_handle(self, payload):
        raise RuntimeError("boom")
    monkeypatch.setattr(AutomationAgent, "handle", fake_handle)

    r = client.post("/automate/run", json={"payload": {"x": 1}})
    assert r.status_code == 500


def test_integration_router_success(monkeypatch):
    def fake_handle(self, payload):
        return {"ok": True}
    monkeypatch.setattr(IntegrationAgent, "handle", fake_handle)

    r = client.post("/n8n/run", json={"payload": {"y": 2}})
    assert r.status_code == 200
    assert r.json()["result"]["ok"] is True


def test_integration_router_error(monkeypatch):
    def fake_handle(self, payload):
        raise RuntimeError("boom")
    monkeypatch.setattr(IntegrationAgent, "handle", fake_handle)

    r = client.post("/n8n/run", json={"payload": {"y": 2}})
    assert r.status_code == 500
