



import asyncio
from backend.services.llm_service import LLMService
from backend.utils.env_setup import get_logger

class KnowledgeAgent:
	def __init__(self):
		self.llm_service = LLMService()
		self.logger = get_logger("KnowledgeAgent")

	async def handle(self, payload):
		topic = payload.get("topic", "AI automation")
		model = payload.get("model")  # If not provided, LLMService will use default from .env
		prompt = f"Summarize the latest developments in {topic}."
		self.logger.info(f"Received knowledge request for topic: {topic}, model: {model}")
		try:
			result = await self.llm_service.generate(prompt, model=model)
			summary = result.get("choices", [{}])[0].get("text", "")
			self.logger.info(f"Summary generated for topic '{topic}' at request time.")
			return {"summary": summary, "raw_response": result}
		except Exception as e:
			self.logger.error(f"Error generating summary for topic '{topic}': {e}")
			return {"error": str(e)}
