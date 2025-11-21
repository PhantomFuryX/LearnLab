import os
import asyncio
from typing import Optional, Dict, Any
from backend.utils.env_setup import get_logger

# Try imports for both modern split packages and legacy monolith
ChatOpenAI = None
OpenAI_LLM = None
try:
	from langchain_openai import ChatOpenAI as _ChatOpenAI, OpenAI as _OpenAI
	ChatOpenAI = _ChatOpenAI
	OpenAI_LLM = _OpenAI
except Exception:
	try:
		# Legacy (older langchain versions)
		from langchain.chat_models import ChatOpenAI as _LegacyChatOpenAI  # type: ignore
		from langchain.llms import OpenAI as _LegacyOpenAI  # type: ignore
		ChatOpenAI = _LegacyChatOpenAI
		OpenAI_LLM = _LegacyOpenAI
	except Exception:
		pass


class LangChainManager:
	"""Unified LangChain interface for LLM calls."""
	def __init__(self):
		self.logger = get_logger("LangChainManager")

	async def a_generate(
		self,
		provider: str,
		model: str,
		prompt: str,
		max_tokens: Optional[int] = None,
		temperature: Optional[float] = None,
		api_key: Optional[str] = None,
	) -> Dict[str, Any]:
		"""Async wrapper around sync generation via asyncio.to_thread."""
		return await asyncio.to_thread(
			self._generate_sync, provider, model, prompt, max_tokens, temperature, api_key
		)

	def _generate_sync(
		self,
		provider: str,
		model: str,
		prompt: str,
		max_tokens: Optional[int] = None,
		temperature: Optional[float] = None,
		api_key: Optional[str] = None,
	) -> Dict[str, Any]:
		provider = (provider or "").lower()
		if provider == "openai":
			return self._openai_sync(model, prompt, max_tokens, temperature, api_key)
		elif provider == "anthropic":
			return {"error": "Anthropic via LangChain not yet implemented. Install langchain-anthropic and wire up ChatAnthropic."}
		elif provider == "deepseek":
			return {"error": "DeepSeek via LangChain not yet implemented. Consider configuring an OpenAI-compatible base_url with langchain-openai."}
		else:
			return {"error": f"Provider '{provider}' not supported in LangChainManager"}

	def _openai_sync(
		self,
		model: str,
		prompt: str,
		max_tokens: Optional[int],
		temperature: Optional[float],
		api_key: Optional[str],
	) -> Dict[str, Any]:
		if ChatOpenAI is None and OpenAI_LLM is None:
			return {
				"error": "LangChain OpenAI wrappers not available. Install 'langchain-openai' or use a langchain version that includes OpenAI integrations.",
			}

		# Ensure environment key present if not passed explicitly
		if api_key:
			os.environ.setdefault("OPENAI_API_KEY", api_key)

		# Choose Chat vs Completions style based on model name
		m = (model or "").strip()
		use_completions = m.endswith("-instruct") or m.startswith("text-")

		params: Dict[str, Any] = {
			"model": model,
			"temperature": 0.2 if temperature is None else temperature,
		}
		if max_tokens is not None:
			params["max_tokens"] = max_tokens

		# Optional timeouts/retries if supported by installed wrapper
		timeout_env = os.getenv("OPENAI_HTTP_TIMEOUT")
		retries_env = os.getenv("OPENAI_HTTP_RETRIES")
		if timeout_env:
			try:
				params["timeout"] = float(timeout_env)
			except Exception:
				pass
		if retries_env:
			try:
				params["max_retries"] = int(retries_env)
			except Exception:
				pass

		try:
			if not use_completions and ChatOpenAI is not None:
				llm = ChatOpenAI(**params)
				msg = llm.invoke(prompt)  # returns BaseMessage
				text = getattr(msg, "content", str(msg))
			else:
				if OpenAI_LLM is None:
					return {"error": "Completions LLM not available. Please install 'langchain-openai' providing OpenAI LLM support."}
				llm = OpenAI_LLM(**params)
				text = llm.predict(prompt)

			return {
				"provider": "openai",
				"model": model,
				"choices": [{"text": text}],
			}
		except Exception as e:
			self.logger.error(f"LangChain OpenAI call failed: {type(e).__name__}: {e}")
			return {"error": f"{type(e).__name__}: {e}"}
