
from fastapi import APIRouter, HTTPException
from backend.core.agents.integration_agent import IntegrationAgent
from pydantic import BaseModel

router = APIRouter()
integration_agent = IntegrationAgent()

class IntegrationRequest(BaseModel):
	payload: dict

@router.post("/run")
async def run_integration(request: IntegrationRequest):
	try:
		# In a real app, this could be async
		result = integration_agent.handle(request.payload)
		return {"result": result}
	except Exception as e:
		raise HTTPException(status_code=500, detail=str(e))
