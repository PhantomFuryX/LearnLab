
import httpx
import os
from backend.utils.env_setup import get_logger

N8N_WEBHOOK_URL = os.getenv("N8N_WEBHOOK_URL", "http://localhost:5678/webhook/ai-automation")

class N8NService:
	def __init__(self, webhook_url: str = None):
		self.webhook_url = webhook_url or N8N_WEBHOOK_URL
		self.logger = get_logger("N8NService")

	async def trigger_workflow(self, action: str, data: dict):
		payload = {"action": action, "data": data}
		self.logger.info(f"Triggering n8n workflow: action={action}, data={data}")
		try:
			async with httpx.AsyncClient() as client:
				response = await client.post(self.webhook_url, json=payload)
				response.raise_for_status()
				self.logger.info(f"n8n workflow triggered successfully for action={action}")
				return response.json()
		except Exception as e:
			self.logger.error(f"Error triggering n8n workflow: {e}")
			return {"error": str(e)}
