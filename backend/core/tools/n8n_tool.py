from __future__ import annotations
from typing import Any, Dict
from backend.services.n8n_service import N8NService
from backend.utils.env_setup import get_logger

class N8NTool:
    name = "n8n"

    def __init__(self) -> None:
        self.logger = get_logger("N8NTool")
        self.svc = N8NService()

    def run(self, action: str, data: Dict[str, Any]) -> Dict[str, Any]:
        # Synchronous wrapper for the async service
        import asyncio
        async def _go():
            return await self.svc.trigger_workflow(action, data)
        try:
            return asyncio.get_event_loop().run_until_complete(_go())
        except RuntimeError:
            # If no running loop
            return asyncio.new_event_loop().run_until_complete(_go())
