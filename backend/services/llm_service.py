import os
import asyncio
from backend.utils.env_setup import get_logger
from backend.services.langchain_manager import LangChainManager
from backend.utils.ratelimit import AsyncRateLimiter
from backend.utils.tracing import span
from backend.services.cache_service import CacheService

try:
	from aiolimiter import AsyncLimiter  # type: ignore
	HAS_AIOLIMITER = True
except Exception:
	HAS_AIOLIMITER = False

# Optional import for streaming
try:
	from langchain_openai import ChatOpenAI as _StreamChatOpenAI
	HAS_STREAM_CHAT = True
except Exception:
	_StreamChatOpenAI = None  # type: ignore
	HAS_STREAM_CHAT = False

try:
	import anthropic  # type: ignore
	HAS_ANTHROPIC = True
except Exception:
	HAS_ANTHROPIC = False

try:
	import tiktoken  # type: ignore
	HAS_TK = True
except Exception:
	HAS_TK = False
try:
	from prometheus_client import Counter  # type: ignore
	TOK_COUNTER = Counter('llm_tokens_total', 'Estimated LLM tokens', ['provider','model','type'])
except Exception:
	TOK_COUNTER = None

class LLMService:
	def __init__(self, provider: str = None, default_model: str = None):
		self.provider = provider or os.getenv("LLM_PROVIDER", "openai")
		self.default_model = default_model or os.getenv("LLM_MODEL", "gpt-4o-mini")
		self.logger = get_logger("LLMService")
		self.lc = LangChainManager()
		self.cache = CacheService()
		# Optional rate limiter
		try:
			rate = float(os.getenv("LLM_RATE_PER_SEC", "0"))
			if rate > 0:
				self._limiter = AsyncLimiter(max_rate=rate, time_period=1) if HAS_AIOLIMITER else AsyncRateLimiter(rate)
			else:
				self._limiter = None
		except Exception:
			self._limiter = None

	def _get_api_key(self, provider: str):
		if provider == "openai":
			return os.getenv("OPENAI_API_KEY", "")
		elif provider == "anthropic":
			return os.getenv("ANTHROPIC_API_KEY", "")
		elif provider == "deepseek":
			return os.getenv("DEEPSEEK_API_KEY", "")
		return ""

	async def generate(self, prompt: str, model: str = None, provider: str = None, **kwargs):
		provider = provider or self.provider
		model = model or self.default_model
		
		# Check cache first
		use_cache = kwargs.get("use_cache", True)
		if use_cache:
			cache_key = self.cache.generate_key("llm_generate", provider, model, prompt, **kwargs)
			cached_result = self.cache.get(cache_key)
			if cached_result:
				self.logger.info(f"Cache hit for LLM request: {cache_key[:8]}")
				return cached_result

		api_key = self._get_api_key(provider)
		self.logger.info(f"LLM request to provider '{provider}' with model '{model}' and prompt: {prompt[:60]}...")
		self.logger.info(f"Loaded OpenAI API key: {api_key[:6]}...")  # Only log the first few chars for security
		try:
			with span("llm.generate", {"provider": provider, "model": model}):
				if getattr(self, "_limiter", None):
					# aiolimiter vs custom
					if HAS_AIOLIMITER and isinstance(self._limiter, AsyncLimiter):
						async with self._limiter:
							pass
					else:
						await self._limiter.acquire()
				max_tokens = kwargs.get("max_tokens", 256)
				result = await self.lc.a_generate(
					provider=provider,
					model=model,
					prompt=prompt,
					max_tokens=max_tokens,
					temperature=kwargs.get("temperature"),
					api_key=api_key,
				)

				if isinstance(result, dict) and result.get("error"):
					self.logger.error(f"LLM error from provider '{provider}': {result['error']}")
					return result

				self.logger.info(f"LLM response received from provider '{provider}'")
				
				final_result = result
				# Ensure uniform shape with choices[0].text for downstream callers
				if isinstance(result, dict) and result.get("choices"):
					# token metrics (best-effort)
					if TOK_COUNTER and HAS_TK:
						enc = tiktoken.get_encoding('cl100k_base')
						TOK_COUNTER.labels(provider, model, 'prompt').inc(len(enc.encode(prompt)))
						try:
							out_text = result.get('choices',[{}])[0].get('text','')
							TOK_COUNTER.labels(provider, model, 'completion').inc(len(enc.encode(out_text)))
						except Exception:
							pass
				else:
					# Fallback if a custom shape was returned
					text = str(result)
					final_result = {"provider": provider, "model": model, "choices": [{"text": text}]}
				
				# Cache the successful result
				if use_cache:
					self.cache.set(cache_key, final_result)
					
				return final_result
		except Exception as e:
			# Log type of exception for better visibility
			self.logger.error(f"LLM error from provider '{provider}': {type(e).__name__}: {e}")
			return {"error": f"{type(e).__name__}: {e}"}

	async def generate_stream(self, prompt: str, model: str = None, provider: str = None, **kwargs):
		"""Async generator yielding token chunks. Uses provider-native streaming when available; otherwise falls back to chunking a non-streaming response."""
		provider = provider or self.provider
		model = model or self.default_model
		api_key = self._get_api_key(provider)
		chunk_size = int(os.getenv("LLM_STREAM_CHUNK", "100"))
		with span("llm.stream", {"provider": provider, "model": model}):
			if provider == "openai" and HAS_STREAM_CHAT and _StreamChatOpenAI is not None:
				# Ensure env key present
				if api_key:
					os.environ.setdefault("OPENAI_API_KEY", api_key)
				params = {"model": model, "temperature": kwargs.get("temperature", 0.2)}
				try:
					llm = _StreamChatOpenAI(**params)
					async for chunk in llm.astream(prompt):
						text = getattr(chunk, "content", None)
						if text:
							yield text
					return
				except Exception as e:
					self.logger.error(f"Streaming via ChatOpenAI failed: {type(e).__name__}: {e}")
			elif provider == "anthropic" and HAS_ANTHROPIC and api_key:
				try:
					client = anthropic.AsyncAnthropic(api_key=api_key)
					# Use Messages API streaming
					stream = await client.messages.create(
						model=model,
						max_tokens=kwargs.get("max_tokens", 512),
						messages=[{"role": "user", "content": prompt}],
						stream=True,
					)
					async with stream as s:
						async for event in s:
							if getattr(event, "type", "") == "content_block_delta":
								delta = getattr(event, "delta", None)
								if delta and getattr(delta, "type", "") == "text_delta":
									yield getattr(delta, "text", "")
							elif getattr(event, "type", "") == "message_delta":
								continue
							elif getattr(event, "type", "") == "message_stop":
								break
					return
				except Exception as e:
					self.logger.error(f"Anthropic streaming failed: {type(e).__name__}: {e}")
		# Fallback: non-streaming generate, then split
		res = await self.generate(prompt, model=model, provider=provider, **kwargs)
		text = ""
		if isinstance(res, dict):
			text = res.get("choices", [{}])[0].get("text", "")
		for i in range(0, len(text), chunk_size):
			yield text[i:i+chunk_size]

		# After fallback generate, we can emit token metrics
		if TOK_COUNTER and HAS_TK:
			enc = tiktoken.get_encoding('cl100k_base')
			TOK_COUNTER.labels(provider, model, 'prompt').inc(len(enc.encode(prompt)))
			TOK_COUNTER.labels(provider, model, 'completion').inc(len(enc.encode(text)))

	async def _anthropic_generate(self, prompt: str, model: str, api_key: str, **kwargs):
		# Kept for backward compability if called elsewhere
		return await self.lc.a_generate("anthropic", model, prompt, kwargs.get("max_tokens", 256), kwargs.get("temperature"), api_key)

	async def _deepseek_generate(self, prompt: str, model: str, api_key: str, **kwargs):
		# Kept for backward compability if called elsewhere
		return await self.lc.a_generate("deepseek", model, prompt, kwargs.get("max_tokens", 256), kwargs.get("temperature"), api_key)
