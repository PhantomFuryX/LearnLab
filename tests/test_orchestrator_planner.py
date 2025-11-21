import os, sys, json, asyncio
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from backend.core.orchestrator import Orchestrator

class DummyTool:
    def __init__(self):
        pass

class DummyWebFetch(DummyTool):
    def run(self, url, headers=None, **kwargs):
        return {"url": url, "status": 200, "headers": {"Content-Type": "text/html"}, "text": "HELLO WORLD"}

class DummyN8N(DummyTool):
    def run(self, action, data):
        return {"ok": True, "action": action, "data": data}

@pytest.mark.asyncio
async def test_automation_planner_toolcalls(monkeypatch):
    from backend.core.tools import base as base_tools

    # Force advanced planner
    o = Orchestrator()
    o.advanced = True
    o._graph = None  # Force linear execution for testing

    # Monkeypatch LLM plan
    async def fake_generate(prompt, *args, **kwargs):
        if "automation" in prompt.lower() and "plan" in prompt.lower():
             # Return automation plan
             plan = {"actions": [{"type": "n8n", "args": {"action": "deploy", "data": {"env": "stage"}}}]}
             return {"choices": [{"text": json.dumps(plan)}]}
        # Return automation report
        return {"choices": [{"text": "Report: deployed"}]}

    monkeypatch.setattr(o.llm, "generate", fake_generate, raising=False)

    # Monkeypatch tools
    def fake_get(name: str):
        return {"web_fetch": DummyWebFetch, "n8n": DummyN8N}.get(name)
    monkeypatch.setattr(base_tools.ToolRegistry, "get", staticmethod(fake_get))

    s = await o.run({"session_id": "s", "message": "deploy app", "preferred_agent": "automation"})

    # Check steps list for presence of plan and report
    step_names = [step["name"] for step in s.get("steps", [])]
    assert "automation_plan" in step_names
    assert "automation_report" in step_names
    assert s.get("result") == "Report: deployed"

@pytest.mark.asyncio
async def test_integration_planner_toolcalls(monkeypatch):
    from backend.core.tools import base as base_tools

    o = Orchestrator()
    o.advanced = True
    o._graph = None  # Force linear execution for testing

    async def fake_generate(prompt, *args, **kwargs):
        if "integration" in prompt.lower() and "plan" in prompt.lower():
             plan = {"actions": [{"type": "web_fetch", "args": {"url": "https://example.com"}}]}
             return {"choices": [{"text": json.dumps(plan)}]}
        return {"choices": [{"text": "Summary: fetched"}]}

    monkeypatch.setattr(o.llm, "generate", fake_generate, raising=False)

    def fake_get(name: str):
        return {"web_fetch": DummyWebFetch, "n8n": DummyN8N}.get(name)
    monkeypatch.setattr(base_tools.ToolRegistry, "get", staticmethod(fake_get))

    s = await o.run({"session_id": "s", "message": "fetch data", "preferred_agent": "integration"})

    step_names = [step["name"] for step in s.get("steps", [])]
    assert "integration_plan" in step_names
    assert "integration_report" in step_names
    assert s.get("result") == "Summary: fetched"
