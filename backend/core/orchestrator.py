from __future__ import annotations
from typing import Any, Dict, List
from backend.core.base import AgentState, Step
from backend.core.tools.retrieval import RetrievalTool
from backend.core.tools.base import ToolRegistry
from backend.core.agents.automation_agent import AutomationAgent
from backend.core.agents.integration_agent import IntegrationAgent
from backend.services.llm_service import LLMService
from backend.utils.env_setup import get_logger
from backend.utils.tracing import span
import os
import json
from pydantic import BaseModel, ValidationError, field_validator
import uuid

# LangGraph wiring (minimal)
try:
    from langgraph.graph import StateGraph, END
    HAS_LANGGRAPH = True
except Exception:
    HAS_LANGGRAPH = False
    StateGraph = None  # type: ignore
    END = "__END__"


class PlanAction(BaseModel):
    type: str
    args: Dict[str, Any] = {}

    @field_validator('type')
    @classmethod
    def validate_type(cls, v):
        allowed = {"retrieval", "web_fetch", "n8n"}
        if v not in allowed:
            raise ValueError(f"Unsupported action type: {v}")
        return v

class Plan(BaseModel):
    actions: List[PlanAction]
    rationale: str | None = None


class Orchestrator:
    def __init__(self) -> None:
        self.logger = get_logger("Orchestrator")
        self.llm = LLMService()
        self.retrieval = RetrievalTool()
        self.automation = AutomationAgent()
        self.integration = IntegrationAgent()
        self.advanced = os.getenv("GRAPH_ADVANCED_FLOW") == "1"
        self._graph = self._build_graph()

    # ---------- Router ----------
    def _route(self, state: Dict[str, Any]) -> str:
        preferred = state.get("preferred_agent")
        if preferred in {"knowledge", "automation", "integration"}:
            return preferred
        # Optional LLM Router
        if os.getenv("ROUTER_USE_LLM") == "1":
            try:
                msg = state.get("message", "")
                prompt = (
                    "Classify the user's intent for routing to one of: knowledge, automation, integration, fallback.\n"
                    "Return STRICT JSON with keys: intent (string), confidence (0..1). No prose.\n\n"
                    f"User: {msg}\n"
                )
                import asyncio
                out = asyncio.get_event_loop().run_until_complete(self.llm.generate(prompt))
                text = ""
                if isinstance(out, dict):
                    text = out.get("choices", [{}])[0].get("text", "")
                data = json.loads(text.strip())
                intent = str(data.get("intent", "fallback")).lower()
                if intent in {"knowledge", "automation", "integration", "fallback"}:
                    return intent
            except Exception:
                pass
        # Heuristics fallback
        msg = (state.get("message") or "").lower()
        if any(w in msg for w in ["what is", "explain", "docs", "documentation", "how do", "how to", "agent", "rag"]):
            return "knowledge"
        if any(w in msg for w in ["run", "execute", "trigger", "schedule", "deploy", "start job", "automate"]):
            return "automation"
        if any(w in msg for w in ["n8n", "webhook", "integrate", "api call", "send to"]):
            return "integration"
        return "fallback"

    # ---------- Nodes ----------
    def _router_node(self, state: Dict[str, Any]) -> Dict[str, Any]:
        with span("router", {"preferred": state.get("preferred_agent"), "session": state.get("session_id") } ):
            route = self._route(state)
            steps = state.get("steps", []) + [Step(name="router", detail=f"route={route}").model_dump()]
            state.update({"route": route, "steps": steps})
            return state

    def _automation_node(self, state: Dict[str, Any]) -> Dict[str, Any]:
        with span("automation.node", {"session": state.get("session_id")}):
            msg = state.get("message", "")
            # Simple automation logic for non-advanced flow
            plan = Plan(actions=[PlanAction(type="n8n", args={"action": "default", "data": {"message": msg}})])
            
            # Execute plan (simplified)
            actions = []
            steps = state.get("steps", [])
            for act in plan.actions:
                tool_cls = ToolRegistry.get(act.type)
                if tool_cls:
                    try:
                        tool = tool_cls()
                        out = tool.run(act.args.get("action"), act.args.get("data"))
                        actions.append({"tool": act.type, "output": out})
                        steps.append(Step(name="automation", detail="executed", output={"ok": True}).model_dump())
                    except Exception as e:
                        actions.append({"tool": act.type, "error": str(e)})
                        steps.append(Step(name="automation", detail="error", output={"error": str(e)}).model_dump())
            
            state.update({"result": f"Executed {len(actions)} automation actions.", "actions": actions, "steps": steps})
            return state

    def _integration_node(self, state: Dict[str, Any]) -> Dict[str, Any]:
        with span("integration.node", {"session": state.get("session_id")}):
            msg = state.get("message", "")
            # Simple integration logic
            steps = state.get("steps", [])
            steps.append(Step(name="integration", detail="placeholder").model_dump())
            state.update({"result": "Integration placeholder executed.", "steps": steps})
            return state

    # Knowledge basic
    def _knowledge_retrieve(self, state: Dict[str, Any]) -> Dict[str, Any]:
        with span("knowledge.retrieve", {"ns": state.get("namespace"), "k": state.get("k")}):
            ns = state.get("namespace") or "default"
            k = int(state.get("k") or 4)
            out = self.retrieval.run(ns, state.get("message", ""), k=k)
            citations = []
            for i, d in enumerate(out.get("docs", [])):
                m = d.get("metadata", {})
                src = m.get("source") or m.get("id") or f"doc_{i+1}"
                citations.append({"source": src, "metadata": m})
            steps = state.get("steps", []) + [Step(name="retrieve", detail=f"k={k}", output={"count": len(out.get('docs', []))}).model_dump()]
            state.update({"artifacts": {**state.get("artifacts", {}), "docs": out.get("docs", [])}, "citations": citations, "steps": steps})
            return state

    def _limit_context(self, context: str, max_chars: int = 200000) -> str:
        if len(context) > max_chars:
            self.logger.warning(f"Context truncated from {len(context)} to {max_chars} chars")
            return context[:max_chars] + "...(truncated)"
        return context

    async def _knowledge_answer(self, state: Dict[str, Any]) -> Dict[str, Any]:
        with span("knowledge.answer", {"ns": state.get("namespace")}):
            # Build combined context from artifacts
            docs = state.get("artifacts", {}).get("docs", [])
            fetched = state.get("artifacts", {}).get("web_fetch", [])
            contexts = []
            for i, d in enumerate(docs):
                contexts.append(f"[{i+1}] {d.get('text','')}")
            base = len(contexts)
            for j, f in enumerate(fetched or []):
                txt = f.get("text") or f.get("body") or ""
                if txt:
                    contexts.append(f"[{base + j + 1}] {txt}")
            context_str = "\n\n".join(contexts) if contexts else "No context available."
            
            # Limit context size to prevent LLM errors
            context_str = self._limit_context(context_str)
            
            # Format history
            history = state.get("history", [])
            history_str = ""
            for msg in history:
                role = msg.get("role", "user")
                content = msg.get("content", "")
                history_str += f"{role.capitalize()}: {content}\n"

            prompt = (
                "You are a helpful assistant. Using the numbered context below, answer the user's question.\n"
                "Cite sources using bracketed numbers like [1], [2] that map to the context snippets.\n\n"
                f"Context:\n{context_str}\n\n"
                f"History:\n{history_str}\n\n"
                f"Question: {state.get('message','')}\n\n"
                "Answer:"
            )
            res = await self.llm.generate(prompt)
            text = ""
            if isinstance(res, dict):
                text = res.get("choices", [{}])[0].get("text", "")
            steps = state.get("steps", []) + [Step(name="answer", detail="llm.generate", output={"len": len(text)}).model_dump()]
            state.update({"result": text, "steps": steps})
            return state

    async def _knowledge_answer_stream(self, state: Dict[str, Any]):
        """Stream the knowledge answer token by token"""
        with span("knowledge.answer_stream", {"ns": state.get("namespace")}):
            # Build combined context from artifacts
            docs = state.get("artifacts", {}).get("docs", [])
            fetched = state.get("artifacts", {}).get("web_fetch", [])
            contexts = []
            for i, d in enumerate(docs):
                contexts.append(f"[{i+1}] {d.get('text','')}")
            base = len(contexts)
            for j, f in enumerate(fetched or []):
                txt = f.get("text") or f.get("body") or ""
                if txt:
                    contexts.append(f"[{base + j + 1}] {txt}")
            context_str = "\n\n".join(contexts) if contexts else "No context available."
            
            # Limit context size to prevent LLM errors
            context_str = self._limit_context(context_str)

            # Format history
            history = state.get("history", [])
            history_str = ""
            for msg in history:
                role = msg.get("role", "user")
                content = msg.get("content", "")
                history_str += f"{role.capitalize()}: {content}\n"

            prompt = (
                "You are a helpful assistant. Using the numbered context below, answer the user's question.\n"
                "Cite sources using bracketed numbers like [1], [2] that map to the context snippets.\n\n"
                f"Context:\n{context_str}\n\n"
                f"History:\n{history_str}\n\n"
                f"Question: {state.get('message','')}\n\n"
                "Answer:"
            )
            
            # Stream tokens from LLM
            full_text = ""
            async for token in self.llm.generate_stream(prompt):
                full_text += token
                yield f"event: token\ndata: {json.dumps(token)}\n\n"
            
            # Send final step
            steps = state.get("steps", []) + [Step(name="answer", detail="llm.generate_stream", output={"len": len(full_text)}).model_dump()]
            yield f"event: step\ndata: {json.dumps(steps[-1])}\n\n"
            yield "event: done\ndata: {}\n\n"

    # Planning and toolcall for advanced flow (Knowledge)
    async def _knowledge_plan(self, state: Dict[str, Any]) -> Dict[str, Any]:
        with span("knowledge.plan", {"ns": state.get("namespace")}):
            prompt = (
                "You are a planner. Create a JSON plan to gather context for answering the user's question.\n"
                "Allowed actions: retrieval, web_fetch.\n"
                "Prioritize 'retrieval' for questions about internal documentation, existing knowledge, or LearnLab.\n"
                "Use 'web_fetch' only if the user explicitly asks for external info or current events.\n"
                "Return STRICT JSON: {\"actions\":[{\"type\":..., \"args\":{...}}], \"rationale\": \"...\"}. No prose.\n\n"
                f"Question: {state.get('message','')}\n"
                f"Namespace (may be null): {state.get('namespace')}\n"
            )
            res = await self.llm.generate(prompt)
            text = ""
            if isinstance(res, dict):
                text = res.get("choices", [{}])[0].get("text", "")
            try:
                plan = Plan.model_validate_json(text)
                steps = state.get("steps", []) + [Step(name="plan", detail="validated", output=plan.model_dump()).model_dump()]
                state.update({"plan": plan.model_dump(), "steps": steps})
            except ValidationError as e:
                steps = state.get("steps", []) + [Step(name="plan", detail="invalid", output={"error": str(e)[:200]}).model_dump()]
                # Fallback to single retrieval
                state.update({"plan": Plan(actions=[PlanAction(type="retrieval", args={"k": state.get('k', 4)})]).model_dump(), "steps": steps})
            return state

    def _knowledge_toolcall(self, state: Dict[str, Any]) -> Dict[str, Any]:
        with span("knowledge.toolcall", {"actions": len((state.get("plan") or {}).get("actions", []))}):
            plan_dict = state.get("plan") or {}
            try:
                plan = Plan.model_validate(plan_dict)
            except Exception:
                plan = Plan(actions=[PlanAction(type="retrieval", args={"k": state.get('k', 4)})])
            artifacts = state.get("artifacts", {})
            steps = state.get("steps", [])
            for act in plan.actions:
                tool_cls = ToolRegistry.get(act.type)
                if not tool_cls:
                    steps.append(Step(name="toolcall", detail=f"unknown:{act.type}").model_dump())
                    continue
                tool = tool_cls()
                # Safe arg extraction
                a = act.args or {}
                if act.type == "retrieval":
                    ns = state.get("namespace") or a.get("namespace") or "default"
                    k = int(a.get("k", state.get("k", 4)))
                    out = tool.run(ns, state.get("message", ""), k=k)
                    artifacts.setdefault("docs", []).extend(out.get("docs", []))
                    steps.append(Step(name="toolcall", detail="retrieval", output={"count": len(out.get('docs', []))}).model_dump())
                elif act.type == "web_fetch":
                    url = a.get("url")
                    urls = a.get("urls") or ([url] if url else [])
                    headers = a.get("headers")
                    results = []
                    for u in urls:
                        r = tool.run(u, headers=headers)
                        if not r.get("error"):
                            results.append({"url": u, "text": r.get("text", ""), "headers": r.get("headers", {})})
                    artifacts.setdefault("web_fetch", []).extend(results)
                    steps.append(Step(name="toolcall", detail="web_fetch", output={"count": len(results)}).model_dump())
                elif act.type == "n8n":
                    steps.append(Step(name="toolcall", detail="n8n (skipped in knowledge path)").model_dump())
            state.update({"artifacts": artifacts, "steps": steps})
            return state

    # Automation planner flow
    async def _automation_plan(self, state: Dict[str, Any]) -> Dict[str, Any]:
        with span("automation.plan", {"session": state.get("session_id")}):
            prompt = (
                "You are an automation planner. Create a JSON plan of actions to execute the user's request.\n"
                "Allowed actions: n8n, web_fetch.\n"
                "Return STRICT JSON: {\"actions\":[{\"type\":..., \"args\":{...}}], \"rationale\": \"...\"}. No prose.\n\n"
                f"Task: {state.get('message','')}\n"
            )
            res = await self.llm.generate(prompt)
            text = ""
            if isinstance(res, dict):
                text = res.get("choices", [{}])[0].get("text", "")
            try:
                plan = Plan.model_validate_json(text)
                steps = state.get("steps", []) + [Step(name="automation_plan", detail="validated", output=plan.model_dump()).model_dump()]
                state.update({"plan": plan.model_dump(), "steps": steps})
            except ValidationError as e:
                steps = state.get("steps", []) + [Step(name="automation_plan", detail="invalid", output={"error": str(e)[:200]}).model_dump()]
                state.update({"plan": Plan(actions=[PlanAction(type="n8n", args={"action": "noop"})]).model_dump(), "steps": steps})
            return state

    def _automation_toolcall(self, state: Dict[str, Any]) -> Dict[str, Any]:
        with span("automation.toolcall", {"actions": len((state.get("plan") or {}).get("actions", []))}):
            plan_dict = state.get("plan") or {}
            try:
                plan = Plan.model_validate(plan_dict)
            except Exception:
                plan = Plan(actions=[PlanAction(type="n8n", args={"action": "noop"})])
            artifacts = state.get("artifacts", {})
            actions = state.get("actions", [])
            steps = state.get("steps", [])
            for act in plan.actions:
                tool_cls = ToolRegistry.get(act.type)
                if not tool_cls:
                    steps.append(Step(name="toolcall", detail=f"unknown:{act.type}").model_dump())
                    continue
                tool = tool_cls()
                a = act.args or {}
                if act.type == "n8n":
                    action = a.get("action") or "noop"
                    data = a.get("data") or {"message": state.get("message")}
                    try:
                        out = tool.run(action, data)
                    except Exception as e:
                        out = {"error": str(e), "action": action}
                    actions.append({"tool": "n8n", "action": action, "output": out})
                    steps.append(Step(name="toolcall", detail="n8n", output={"ok": not bool(out.get('error'))}).model_dump())
                elif act.type == "web_fetch":
                    url = a.get("url")
                    headers = a.get("headers")
                    if url:
                        r = tool.run(url, headers=headers)
                        artifacts.setdefault("web_fetch", []).append({"url": url, "text": r.get("text", ""), "headers": r.get("headers", {})})
                        steps.append(Step(name="toolcall", detail="web_fetch", output={"ok": not bool(r.get('error'))}).model_dump())
            state.update({"artifacts": artifacts, "actions": actions, "steps": steps})
            return state

    async def _automation_report(self, state: Dict[str, Any]) -> Dict[str, Any]:
        with span("automation.report", {"actions": len(state.get("actions", []))}):
            actions = state.get("actions", [])
            fetched = state.get("artifacts", {}).get("web_fetch", [])
            prompt = (
                "Summarize the results of the automation run in a concise report for the user.\n"
                f"Actions: {json.dumps(actions)[:2000]}\n\n"
                f"Fetched: {json.dumps(fetched)[:2000]}\n\n"
                "Report:"
            )
            res = await self.llm.generate(prompt)
            txt = ""
            if isinstance(res, dict):
                txt = res.get("choices", [{}])[0].get("text", "")
            steps = state.get("steps", []) + [Step(name="automation_report", detail="llm.generate", output={"len": len(txt)}).model_dump()]
            state.update({"result": txt, "steps": steps})
            return state

    # Integration planner flow
    async def _integration_plan(self, state: Dict[str, Any]) -> Dict[str, Any]:
        with span("integration.plan", {"session": state.get("session_id")}):
            prompt = (
                "You are an integration planner. Create a JSON plan to gather external data or call connectors.\n"
                "Allowed actions: web_fetch, n8n.\n"
                "Return STRICT JSON: {\"actions\":[{\"type\":..., \"args\":{...}}], \"rationale\": \"...\"}.\n\n"
                f"Task: {state.get('message','')}\n"
            )
            res = await self.llm.generate(prompt)
            text = ""
            if isinstance(res, dict):
                text = res.get("choices", [{}])[0].get("text", "")
            try:
                plan = Plan.model_validate_json(text)
                steps = state.get("steps", []) + [Step(name="integration_plan", detail="validated", output=plan.model_dump()).model_dump()]
                state.update({"plan": plan.model_dump(), "steps": steps})
            except ValidationError as e:
                steps = state.get("steps", []) + [Step(name="integration_plan", detail="invalid", output={"error": str(e)[:200]}).model_dump()]
                state.update({"plan": Plan(actions=[PlanAction(type="web_fetch", args={"url": "https://example.com"})]).model_dump(), "steps": steps})
            return state

    def _integration_toolcall(self, state: Dict[str, Any]) -> Dict[str, Any]:
        with span("integration.toolcall", {"actions": len((state.get("plan") or {}).get("actions", []))}):
            plan_dict = state.get("plan") or {}
            try:
                plan = Plan.model_validate(plan_dict)
            except Exception:
                plan = Plan(actions=[PlanAction(type="web_fetch", args={"url": "https://example.com"})])
            artifacts = state.get("artifacts", {})
            actions = state.get("actions", [])
            steps = state.get("steps", [])
            for act in plan.actions:
                tool_cls = ToolRegistry.get(act.type)
                if not tool_cls:
                    steps.append(Step(name="toolcall", detail=f"unknown:{act.type}").model_dump())
                    continue
                tool = tool_cls()
                a = act.args or {}
                if act.type == "web_fetch":
                    url = a.get("url")
                    headers = a.get("headers")
                    ok = False
                    if url:
                        r = tool.run(url, headers=headers)
                        ok = not bool(r.get("error"))
                        if ok:
                            artifacts.setdefault("web_fetch", []).append({"url": url, "text": r.get("text", ""), "headers": r.get("headers", {})})
                    steps.append(Step(name="toolcall", detail="web_fetch", output={"ok": ok}).model_dump())
                elif act.type == "n8n":
                    action = a.get("action") or "noop"
                    data = a.get("data") or {"message": state.get("message")}
                    try:
                        out = tool.run(action, data)
                    except Exception as e:
                        out = {"error": str(e), "action": action}
                    actions.append({"tool": "n8n", "action": action, "output": out})
                    steps.append(Step(name="toolcall", detail="n8n", output={"ok": not bool(out.get('error'))}).model_dump())
            state.update({"artifacts": artifacts, "actions": actions, "steps": steps})
            return state

    async def _integration_report(self, state: Dict[str, Any]) -> Dict[str, Any]:
        with span("integration.report", {"fetched": len(state.get("artifacts", {}).get("web_fetch", []))}):
            fetched = state.get("artifacts", {}).get("web_fetch", [])
            actions = state.get("actions", [])
            prompt = (
                "Summarize integrated data and actions for the user in a concise response.\n"
                f"Fetched: {json.dumps(fetched)[:2000]}\n"
                f"Actions: {json.dumps(actions)[:1000]}\n\n"
                "Summary:"
            )
            res = await self.llm.generate(prompt)
            txt = ""
            if isinstance(res, dict):
                txt = res.get("choices", [{}])[0].get("text", "")
            steps = state.get("steps", []) + [Step(name="integration_report", detail="llm.generate", output={"len": len(txt)}).model_dump()]
            state.update({"result": txt, "steps": steps})
            return state

    def _fallback_node(self, state: Dict[str, Any]) -> Dict[str, Any]:
        msg = "I'm not sure which agent to use. Try asking a knowledge question or specify an action."
        steps = state.get("steps", []) + [Step(name="fallback", detail="no-route").model_dump()]
        state.update({"result": msg, "steps": steps})
        return state

    def _build_graph(self):
        if not HAS_LANGGRAPH:
            self.logger.warning("LangGraph not available; orchestrator will run a linear execution.")
            return None
        g = StateGraph(dict)
        g.add_node("router", self._router_node)
        if self.advanced:
            g.add_node("knowledge_plan", self._knowledge_plan)
            g.add_node("knowledge_toolcall", self._knowledge_toolcall)
            g.add_node("knowledge_answer", self._knowledge_answer)
            # Automation advanced
            g.add_node("automation_plan", self._automation_plan)
            g.add_node("automation_toolcall", self._automation_toolcall)
            g.add_node("automation_report", self._automation_report)
            # Integration advanced
            g.add_node("integration_plan", self._integration_plan)
            g.add_node("integration_toolcall", self._integration_toolcall)
            g.add_node("integration_report", self._integration_report)
        else:
            g.add_node("knowledge_retrieve", self._knowledge_retrieve)
            g.add_node("knowledge_answer", self._knowledge_answer)
            g.add_node("automation", self._automation_node)
            g.add_node("integration", self._integration_node)
        g.add_node("fallback", self._fallback_node)

        def decide_route(state: Dict[str, Any]):
            r = state.get("route") or self._route(state)
            if r == "knowledge":
                return "knowledge_plan" if self.advanced else "knowledge_retrieve"
            if r == "automation":
                return "automation_plan" if self.advanced else "automation"
            if r == "integration":
                return "integration_plan" if self.advanced else "integration"
            return "fallback"

        g.set_entry_point("router")
        g.add_conditional_edges("router", decide_route)
        if self.advanced:
            g.add_edge("knowledge_plan", "knowledge_toolcall")
            g.add_edge("knowledge_toolcall", "knowledge_answer")
            g.add_edge("knowledge_answer", END)

            g.add_edge("automation_plan", "automation_toolcall")
            g.add_edge("automation_toolcall", "automation_report")
            g.add_edge("automation_report", END)

            g.add_edge("integration_plan", "integration_toolcall")
            g.add_edge("integration_toolcall", "integration_report")
            g.add_edge("integration_report", END)
        else:
            g.add_edge("knowledge_retrieve", "knowledge_answer")
            g.add_edge("knowledge_answer", END)
            g.add_edge("automation", END)
            g.add_edge("integration", END)
        g.add_edge("fallback", END)
        return g.compile()

    async def run(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        state = AgentState(**payload).model_dump()
        state.setdefault("request_id", str(uuid.uuid4()))
        try:
            if self._graph is None:
                # Linear execution
                state = self._router_node(state)
                r = state.get("route")
                if r == "knowledge":
                    if self.advanced:
                        state = await self._knowledge_plan(state)
                        state = self._knowledge_toolcall(state)
                        state = await self._knowledge_answer(state)
                    else:
                        state = self._knowledge_retrieve(state)
                        state = await self._knowledge_answer(state)
                elif r == "automation":
                    if self.advanced:
                        state = await self._automation_plan(state)
                        state = self._automation_toolcall(state)
                        state = await self._automation_report(state)
                    else:
                        state = self._automation_node(state)
                elif r == "integration":
                    if self.advanced:
                        state = await self._integration_plan(state)
                        state = self._integration_toolcall(state)
                        state = await self._integration_report(state)
                    else:
                        state = self._integration_node(state)
                else:
                    state = self._fallback_node(state)
                return state
            else:
                result_state = await self._graph.ainvoke(state)  # type: ignore
                return result_state
        except Exception as e:
            self.logger.error(f"Orchestrator error: {e}")
            state.setdefault("errors", []).append(str(e))
            return state

    async def stream(self, payload: Dict[str, Any]):
        state = AgentState(**payload).model_dump()
        state.setdefault("request_id", str(uuid.uuid4()))
        try:
            # Router
            state = self._router_node(state)
            yield f"event: step\ndata: {json.dumps(state['steps'][-1])}\n\n"
            r = state.get("route")
            if r == "knowledge":
                if self.advanced:
                    state = await self._knowledge_plan(state)
                    yield f"event: step\ndata: {json.dumps(state['steps'][-1])}\n\n"
                    state = self._knowledge_toolcall(state)
                    yield f"event: step\ndata: {json.dumps(state['steps'][-1])}\n\n"
                else:
                    state = self._knowledge_retrieve(state)
                    yield f"event: step\ndata: {json.dumps(state['steps'][-1])}\n\n"
                async for evt in self._knowledge_answer_stream(state):
                    yield evt
                return
            elif r == "automation":
                if self.advanced:
                    state = await self._automation_plan(state)
                    yield f"event: step\ndata: {json.dumps(state['steps'][-1])}\n\n"
                    state = await self._automation_toolcall(state)
                    yield f"event: step\ndata: {json.dumps(state['steps'][-1])}\n\n"
                    state = await self._automation_report(state)
                    yield f"event: step\ndata: {json.dumps(state['steps'][-1])}\n\n"
                    yield f"event: token\ndata: {json.dumps(state.get('result',''))}\n\n"
                else:
                    state = self._automation_node(state)
                    yield f"event: step\ndata: {json.dumps(state['steps'][-1])}\n\n"
                    yield f"event: token\ndata: {json.dumps(state.get('result',''))}\n\n"
                yield f"event: done\ndata: \n\n"
                return
            elif r == "integration":
                if self.advanced:
                    state = await self._integration_plan(state)
                    yield f"event: step\ndata: {json.dumps(state['steps'][-1])}\n\n"
                    state = self._integration_toolcall(state)
                    yield f"event: step\ndata: {json.dumps(state['steps'][-1])}\n\n"
                    state = await self._integration_report(state)
                    yield f"event: step\ndata: {json.dumps(state['steps'][-1])}\n\n"
                    yield f"event: token\ndata: {json.dumps(state.get('result',''))}\n\n"
                else:
                    state = self._integration_node(state)
                    yield f"event: step\ndata: {json.dumps(state['steps'][-1])}\n\n"
                    yield f"event: token\ndata: {json.dumps(state.get('result',''))}\n\n"
                yield f"event: done\ndata: \n\n"
                return
            else:
                state = self._fallback_node(state)
                yield f"event: step\ndata: {json.dumps(state['steps'][-1])}\n\n"
                yield f"event: token\ndata: {json.dumps(state.get('result',''))}\n\n"
                yield f"event: done\ndata: \n\n"
                return
        except Exception as e:
            self.logger.error(f"Orchestrator stream error: {e}")
            yield f"event: error\ndata: {json.dumps(str(e))}\n\n"
            yield f"event: done\ndata: \n\n"
