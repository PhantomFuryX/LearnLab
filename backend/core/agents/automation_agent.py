from backend.utils.env_setup import get_logger
from typing import Any, Dict, Optional
from pydantic import BaseModel

class AutomationInput(BaseModel):
	message: Optional[str] = None
	n8n_action: Optional[str] = None
	data: Optional[Dict[str, Any]] = None

class AutomationOutput(BaseModel):
	result: str
	payload: Dict[str, Any]
	n8n_response: Optional[Dict[str, Any]] = None

class AutomationAgent:
	"""Handles simple automation tasks. Synchronous handle for brevity.
	If payload contains {"raise": true} it will raise a ValueError to exercise error paths in tests.
	Optionally triggers n8n via provided action/data.
	"""
	name = "automation"
	tools = ["n8n"]
	input_model = AutomationInput
	output_model = AutomationOutput

	def __init__(self) -> None:
		self.logger = get_logger("AutomationAgent")
		# Lazy import to avoid circulars
		from backend.core.tools.n8n_tool import N8NTool  # type: ignore
		self._n8n = N8NTool()

	def handle(self, payload: Dict[str, Any]) -> Dict[str, Any]:
		self.logger.info(f"Received automation request: {payload}")
		if payload and payload.get("raise"):
			raise ValueError("AutomationAgent simulated error as requested")
		resp: Optional[Dict[str, Any]] = None
		try:
			inp = self.input_model(**(payload or {}))
			if inp.n8n_action:
				resp = self._n8n.run(inp.n8n_action, inp.data or {})
		except Exception as e:
			self.logger.error(f"AutomationAgent tool error: {e}")
		result = {"result": "AutomationAgent handled the task", "payload": payload}
		if resp is not None:
			result["n8n_response"] = resp
		self.logger.info("Automation task handled successfully.")
		# Validate output shape
		return self.output_model(**result).model_dump()
