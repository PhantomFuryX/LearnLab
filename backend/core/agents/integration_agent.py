from backend.utils.env_setup import get_logger
from typing import Any, Dict, Optional, List
from pydantic import BaseModel

class IntegrationInput(BaseModel):
	message: Optional[str] = None
	fetch_url: Optional[str] = None
	fetch_urls: Optional[List[str]] = None
	headers: Optional[Dict[str, str]] = None

class IntegrationOutput(BaseModel):
	result: str
	payload: Dict[str, Any]
	fetch_results: Optional[List[Dict[str, Any]]] = None

class IntegrationAgent:
	"""Handles external integration tasks. Synchronous for simplicity.
	If payload contains {"raise": true} it will raise a ValueError for testing error handling.
	Optionally fetches web content using WebFetchTool.
	"""
	name = "integration"
	tools = ["web_fetch"]
	input_model = IntegrationInput
	output_model = IntegrationOutput

	def __init__(self) -> None:
		self.logger = get_logger("IntegrationAgent")
		from backend.core.tools.web_fetch import WebFetchTool  # type: ignore
		self._fetch = WebFetchTool()

	def handle(self, payload: Dict[str, Any]) -> Dict[str, Any]:
		self.logger.info(f"Received integration request: {payload}")
		if payload and payload.get("raise"):
			raise ValueError("IntegrationAgent simulated error as requested")
		fetch_results: Optional[List[Dict[str, Any]]] = None
		try:
			inp = self.input_model(**(payload or {}))
			urls: List[str] = []
			if inp.fetch_url:
				urls.append(inp.fetch_url)
			if inp.fetch_urls:
				urls.extend(inp.fetch_urls)
			if urls:
				fetch_results = [self._fetch.run(u, headers=inp.headers) for u in urls]
		except Exception as e:
			self.logger.error(f"IntegrationAgent tool error: {e}")
		result = {"result": "IntegrationAgent handled the task", "payload": payload}
		if fetch_results is not None:
			result["fetch_results"] = fetch_results
		self.logger.info("Integration task handled successfully.")
		return self.output_model(**result).model_dump()
