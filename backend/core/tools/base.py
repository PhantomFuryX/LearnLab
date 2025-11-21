from __future__ import annotations
from typing import Protocol, Dict, Any, Optional, Type
from pydantic import BaseModel
from backend.utils.env_setup import get_logger

class Tool(Protocol):
    name: str
    def run(self, *args, **kwargs) -> Dict[str, Any]:
        ...

class ToolRegistry:
    _registry: Dict[str, type] = {}
    _logger = get_logger("ToolRegistry")

    @classmethod
    def register(cls, name: str, tool_cls: type):
        cls._registry[name] = tool_cls
        cls._logger.info(f"Registered tool: {name} -> {tool_cls!r}")

    @classmethod
    def get(cls, name: str) -> Optional[type]:
        return cls._registry.get(name)

# Register built-ins lazily (to avoid import cycles)
try:
    from backend.core.tools.retrieval import RetrievalTool  # type: ignore
    ToolRegistry.register("retrieval", RetrievalTool)
except Exception:
    pass

try:
    from backend.core.tools.web_fetch import WebFetchTool  # type: ignore
    ToolRegistry.register("web_fetch", WebFetchTool)
except Exception:
    pass

try:
    from backend.core.tools.n8n_tool import N8NTool  # type: ignore
    ToolRegistry.register("n8n", N8NTool)
except Exception:
    pass
