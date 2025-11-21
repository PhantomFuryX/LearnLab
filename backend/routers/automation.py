
from fastapi import APIRouter, HTTPException
from backend.core.agents.automation_agent import AutomationAgent
from pydantic import BaseModel

router = APIRouter()
automation_agent = AutomationAgent()

class AutomationRequest(BaseModel):
	payload: dict

@router.post("/run")
async def run_automation(request: AutomationRequest):
	try:
		# In a real app, this could be async
		result = automation_agent.handle(request.payload)
		return {"result": result}
	except Exception as e:
		raise HTTPException(status_code=500, detail=str(e))
