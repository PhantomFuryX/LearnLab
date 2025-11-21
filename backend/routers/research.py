"""
Research API endpoints
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from backend.core.agents.research_agent import ResearchAgent
from backend.services.research_storage_service import ResearchStorageService
from backend.utils.env_setup import get_logger

router = APIRouter()
logger = get_logger()

class ResearchRequest(BaseModel):
    query: str
    namespace: Optional[str] = "default"
    sources: Optional[List[str]] = None  # ["arxiv", "web", "all"]
    max_results: Optional[int] = 10
    store: bool = True  # Store results in DB


class ResearchResponse(BaseModel):
    query: str
    timestamp: str
    results: List[dict]
    total: int
    stored_id: Optional[str] = None


@router.post("/search", response_model=ResearchResponse)
async def search_research(request: ResearchRequest):
    """
    Search for research papers and articles.
    
    Example:
    ```json
    {
        "query": "agentic AI architectures",
        "sources": ["arxiv", "web"],
        "max_results": 10,
        "namespace": "ai-research"
    }
    ```
    """
    try:
        agent = ResearchAgent()
        
        if request.store:
            # Search and store
            results = await agent.search_and_store(
                query=request.query,
                namespace=request.namespace,
                sources=request.sources,
                max_results=request.max_results
            )
        else:
            # Search only (don't store)
            results = await agent.search(
                query=request.query,
                sources=request.sources,
                max_results=request.max_results
            )
        
        return {
            "query": results["query"],
            "timestamp": results["timestamp"].isoformat(),
            "results": results["results"],
            "total": results["total"],
            "stored_id": results.get("stored_id")
        }
    except Exception as e:
        logger.error(f"Research search failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history")
async def get_research_history(
    namespace: Optional[str] = None,
    limit: int = 50,
    skip: int = 0
):
    """Get research history (past queries)."""
    try:
        storage = ResearchStorageService()
        history = storage.list_research(namespace=namespace, limit=limit, skip=skip)
        return {"history": history, "count": len(history)}
    except Exception as e:
        logger.error(f"Failed to get research history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/results/{research_id}")
async def get_research_results(research_id: str):
    """Get specific research results by ID."""
    try:
        storage = ResearchStorageService()
        results = storage.get_research(research_id)
        
        if not results:
            raise HTTPException(status_code=404, detail="Research not found")
        
        return results
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get research results: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/results/{research_id}")
async def delete_research(research_id: str):
    """Delete research results."""
    try:
        storage = ResearchStorageService()
        deleted = storage.delete_research(research_id)
        
        if not deleted:
            raise HTTPException(status_code=404, detail="Research not found")
        
        return {"message": "Research deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete research: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/feed")
async def get_research_feed(limit: int = 50):
    """Get a mixed feed of recent research items."""
    try:
        storage = ResearchStorageService()
        feed = storage.get_feed(limit=limit)
        return feed
    except Exception as e:
        logger.error(f"Failed to get feed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
