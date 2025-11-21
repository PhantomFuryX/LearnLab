from fastapi import APIRouter, HTTPException, Request, Depends
from backend.utils.schema import LLMRequest, LLMResponse
from backend.services.llm_service import LLMService
from backend.services.chat_service import ChatService
import asyncio
from typing import Optional, Dict, Any, List
from fastapi.responses import StreamingResponse
from backend.core.orchestrator import Orchestrator
from backend.core.agents.code_agent import CodeAgent
from pydantic import BaseModel
import uuid
import json

router = APIRouter()
llm_service = LLMService()
chat_service = ChatService()
orch = Orchestrator()

# Session Models
class CreateSessionRequest(BaseModel):
    title: Optional[str] = "New Chat"

class UpdateSessionRequest(BaseModel):
    title: str

@router.get("/sessions")
async def list_sessions(request: Request):
    user = getattr(request.state, "user", None)
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")
    return chat_service.get_user_sessions(user["id"])

@router.post("/sessions")
async def create_session(body: CreateSessionRequest, request: Request):
    user = getattr(request.state, "user", None)
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")
    sess_id = chat_service.create_session(user["id"], body.title)
    return {"id": sess_id, "title": body.title}

@router.get("/sessions/{session_id}/messages")
async def get_session_messages(session_id: str, request: Request):
    user = getattr(request.state, "user", None)
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")
    # TODO: Check ownership if strictly needed, but ID is random enough for now
    msgs = chat_service.get_messages(session_id)
    return msgs

@router.delete("/sessions/{session_id}")
async def delete_session(session_id: str, request: Request):
    user = getattr(request.state, "user", None)
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")
    if chat_service.delete_session(session_id, user["id"]):
        return {"status": "deleted"}
    raise HTTPException(status_code=404, detail="Session not found")

@router.patch("/sessions/{session_id}")
async def update_session(session_id: str, body: UpdateSessionRequest, request: Request):
    user = getattr(request.state, "user", None)
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")
    if chat_service.update_session_title(session_id, body.title, user["id"]):
        return {"status": "updated"}
    raise HTTPException(status_code=404, detail="Session not found")


@router.post("/llm", response_model=LLMResponse)
async def llm_generate(request: LLMRequest):
	try:
		result = await llm_service.generate(
			prompt=request.prompt,
			model=request.model,
			max_tokens=request.max_tokens,
			provider=request.provider
		)
		return LLMResponse(result=result.get("choices", [{}])[0].get("text", ""), raw_response=result)
	except Exception as e:
		raise HTTPException(status_code=500, detail=str(e))

class AskPayload(LLMRequest):
	# Extend to allow orchestrator-based ask
	namespace: Optional[str] = None
	k: int = 4
	preferred_agent: Optional[str] = None
	mode: Optional[str] = None  # For tutor mode (walkthrough, code_review)
	session_id: Optional[str] = None

@router.post("/ask")
async def chat_ask(payload: AskPayload, request: Request):
	user = getattr(request.state, "user", None)
	try:
		# Handle history if session_id provided
		history = []
		if payload.session_id and user:
			chat_service.add_message(payload.session_id, "user", payload.prompt)
			history = chat_service.get_messages(payload.session_id)
			# Remove current message from history to avoid duplication in context if implementation separates them
			if history and history[-1]['content'] == payload.prompt:
				history.pop()

		state = await orch.run({
			"session_id": payload.session_id or "chat",
			"message": payload.prompt,
			"namespace": payload.namespace,
			"k": payload.k,
			"preferred_agent": payload.preferred_agent or "knowledge",
			"history": history
		})
		
		ans = state.get("result")
		if payload.session_id and user and ans:
			chat_service.add_message(payload.session_id, "assistant", ans)

		return {"request_id": state.get("request_id"), "answer": ans, "steps": state.get("steps", []), "citations": state.get("citations", [])}
	except Exception as e:
		raise HTTPException(status_code=500, detail=str(e))

import json
from backend.core.agents.tutor_agent import TutorAgent

@router.post("/ask_stream")
async def chat_ask_stream(payload: AskPayload, request: Request):
	"""Stream tokens from the orchestrator's knowledge path using SSE."""
	try:
		rid = str(uuid.uuid4())
		user = getattr(request.state, "user", None)
		
		# Setup history
		history = []
		if payload.session_id and user:
			# Check if session exists, if not just ignore (or maybe we should error?)
			# Assuming session exists because frontend created it.
			chat_service.add_message(payload.session_id, "user", payload.prompt)
			all_msgs = chat_service.get_messages(payload.session_id)
			# Filter out the message we just added so it's not in "history" part of prompt
			history = [m for m in all_msgs if m['content'] != payload.prompt or m['role'] != 'user']

		# If mode is 'tutor', use TutorAgent directly
		if payload.preferred_agent == 'tutor':
			tutor = TutorAgent()
			
			# Run Tutor chat (streaming not yet implemented in TutorAgent, so we mock stream)
			async def tutor_stream():
				res = await tutor.chat(
					message=payload.prompt,
					history=history, # Pass real history
					mode=payload.mode or "general"
				)
				# Stream the response text
				text = res.get("response", "")
				yield f"event: token\ndata: {json.dumps(text)}\n\n"
				yield f"event: step\ndata: {json.dumps({'name': 'tutor', 'detail': 'generated'})}\n\n"
				yield "event: done\ndata: {}\n\n"
				
				if payload.session_id and user:
					chat_service.add_message(payload.session_id, "assistant", text)

			return StreamingResponse(tutor_stream(), media_type="text/event-stream", headers={"X-Request-ID": rid})

		# Default Orchestrator stream
		gen = orch.stream({
			"session_id": payload.session_id or "chat",
			"message": payload.prompt,
			"namespace": payload.namespace,
			"k": payload.k,
			"preferred_agent": payload.preferred_agent or "knowledge",
			"request_id": rid,
			"history": history
		})
		
		async def wrapped_stream():
			full_text = ""
			async for chunk in gen:
				# Accumulate text from tokens
				if chunk.startswith("event: token"):
					try:
						# format is "event: token\ndata: "token_str"\n\n"
						lines = chunk.split('\n')
						for ln in lines:
							if ln.startswith('data:'):
								val = json.loads(ln[5:].strip())
								full_text += val
					except:
						pass
				yield chunk
			
			if payload.session_id and user and full_text:
				chat_service.add_message(payload.session_id, "assistant", full_text)

		return StreamingResponse(wrapped_stream(), media_type="text/event-stream", headers={"X-Request-ID": rid})
	except Exception as e:
		raise HTTPException(status_code=500, detail=str(e))

class CodeGenChatRequest(BaseModel):
	topic: str
	stack: str = "langchain"
	language: str = "python"

@router.post("/generate-code")
async def generate_code_from_chat(request: CodeGenChatRequest):
	"""Generate code directly from a topic/description in chat."""
	try:
		# Create a simple summary from the topic
		summary = {
			"headline": request.topic,
			"tldr": f"Code example for: {request.topic}",
			"key_points": [request.topic],
			"methods": [],
			"applications": []
		}
		
		# Generate code
		agent = CodeAgent()
		code_example = await agent.generate_code(
			summary=summary,
			stack=request.stack,
			language=request.language,
			include_tests=True
		)
		
		return {
			"topic": request.topic,
			"stack": request.stack,
			"language": request.language,
			"code": code_example.model_dump()
		}
	except Exception as e:
		raise HTTPException(status_code=500, detail=str(e))
