from __future__ import annotations
from typing import Any, Dict, List, Optional
from backend.services.rag_service import RAGService
from backend.utils.env_setup import get_logger

class RetrievalTool:
    name = "retrieval"

    def __init__(self) -> None:
        self.rag = RAGService()
        self.logger = get_logger("RetrievalTool")

    def run(self, namespace: str, query: str, k: int = 4) -> Dict[str, Any]:
        self.logger.info(f"RetrievalTool: namespace={namespace}, k={k}")
        docs = self.rag.retrieve(namespace, query, k=k)
        results: List[Dict[str, Any]] = []
        for d in docs:
            meta = getattr(d, "metadata", {}) or {}
            results.append({
                "text": getattr(d, "page_content", ""),
                "metadata": meta,
            })
        return {"docs": results}
