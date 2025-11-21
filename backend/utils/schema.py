from pydantic import BaseModel
from typing import Optional, Any

class LLMRequest(BaseModel):
	prompt: str
	model: Optional[str] = None
	# Use OpenAI-compatible name
	max_tokens: Optional[int] = 256
	provider: Optional[str] = "openai"

class LLMResponse(BaseModel):
	result: Any
	raw_response: Any
