from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any
from backend.core.orchestrator import Orchestrator
from fastapi.responses import StreamingResponse

router = APIRouter()
orch = Orchestrator()

class RunAgentsRequest(BaseModel):
    session_id: str
    message: str
    preferred_agent: Optional[str] = None  # knowledge | automation | integration
    namespace: Optional[str] = None
    k: int = 4
    context: Optional[Dict[str, Any]] = None

@router.post("/run")
async def run_agents(req: RunAgentsRequest):
    try:
        state = await orch.run(req.model_dump())
        return {
            "request_id": state.get("request_id"),
            "final": state.get("result"),
            "steps": state.get("steps", []),
            "citations": state.get("citations", []),
            "actions": state.get("actions", []),
            "errors": state.get("errors", []),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/stream")
async def run_agents_stream(req: RunAgentsRequest):
    try:
        # Generate a request id here to expose in headers even before orchestrator returns state
        import uuid
        rid = str(uuid.uuid4())
        gen = orch.stream({**req.model_dump(), "request_id": rid})
        return StreamingResponse(gen, media_type="text/event-stream", headers={"X-Request-ID": rid})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
