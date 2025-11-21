"""
Summarization API endpoints
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from backend.core.agents.summarizer_agent import SummarizerAgent
from backend.services.summary_storage_service import SummaryStorageService
from backend.services.research_storage_service import ResearchStorageService
from backend.utils.env_setup import get_logger

router = APIRouter()
logger = get_logger()

class SummarizeRequest(BaseModel):
    research_id: str  # ID of research to summarize
    aggregate: bool = True  # Create aggregate summary
    namespace: Optional[str] = "default"


class SummarizeDirectRequest(BaseModel):
    """Summarize arbitrary results without research_id"""
    results: List[dict]
    query: str
    aggregate: bool = True
    namespace: Optional[str] = "default"


@router.post("/research/{research_id}")
async def summarize_research(research_id: str, aggregate: bool = True):
    """
    Summarize research results by research ID.
    
    Example: POST /summarize/research/abc-123?aggregate=true
    """
    try:
        # Get research results
        research_storage = ResearchStorageService()
        research = research_storage.get_research(research_id)
        
        if not research:
            raise HTTPException(status_code=404, detail="Research not found")
        
        results = research.get("results", [])
        if not results:
            raise HTTPException(status_code=400, detail="No results to summarize")
        
        # Summarize
        agent = SummarizerAgent()
        summaries_data = await agent.summarize_multiple(results, aggregate=aggregate)
        
        # Handle both list and dict responses
        if isinstance(summaries_data, dict):
            # Has aggregate
            summaries = summaries_data["individual_summaries"]
            aggregate_summary = summaries_data.get("aggregate_summary")
        else:
            summaries = summaries_data
            aggregate_summary = None
        
        # Store summaries
        storage = SummaryStorageService()
        summary_id = storage.store_summary(
            research_id=research_id,
            query=research.get("query", ""),
            summaries=summaries,
            aggregate_summary=aggregate_summary,
            namespace=research.get("namespace", "default")
        )
        
        return {
            "summary_id": summary_id,
            "research_id": research_id,
            "summaries": summaries,
            "aggregate_summary": aggregate_summary,
            "total": len(summaries)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Summarization failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/direct")
async def summarize_direct(request: SummarizeDirectRequest):
    """
    Summarize results directly without research_id.
    
    Example:
    ```json
    {
        "query": "AI agents",
        "results": [
            {"title": "...", "excerpt": "...", "source": "arxiv", "link": "..."}
        ],
        "aggregate": true
    }
    ```
    """
    try:
        agent = SummarizerAgent()
        summaries_data = await agent.summarize_multiple(
            request.results, 
            aggregate=request.aggregate
        )
        
        # Handle both formats
        if isinstance(summaries_data, dict):
            summaries = summaries_data["individual_summaries"]
            aggregate_summary = summaries_data.get("aggregate_summary")
        else:
            summaries = summaries_data
            aggregate_summary = None
        
        # Store
        storage = SummaryStorageService()
        summary_id = storage.store_summary(
            research_id="direct",
            query=request.query,
            summaries=summaries,
            aggregate_summary=aggregate_summary,
            namespace=request.namespace
        )
        
        return {
            "summary_id": summary_id,
            "summaries": summaries,
            "aggregate_summary": aggregate_summary,
            "total": len(summaries)
        }
        
    except Exception as e:
        logger.error(f"Direct summarization failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/list")
async def list_summaries(
    namespace: Optional[str] = None,
    limit: int = 50,
    skip: int = 0
):
    """Get list of summaries."""
    try:
        storage = SummaryStorageService()
        summaries = storage.list_summaries(namespace=namespace, limit=limit, skip=skip)
        return {"summaries": summaries, "count": len(summaries)}
    except Exception as e:
        logger.error(f"Failed to list summaries: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{summary_id}")
async def get_summary(summary_id: str):
    """Get specific summary by ID."""
    try:
        storage = SummaryStorageService()
        summary = storage.get_summary(summary_id)
        
        if not summary:
            raise HTTPException(status_code=404, detail="Summary not found")
        
        return summary
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{summary_id}")
async def delete_summary(summary_id: str):
    """Delete summary."""
    try:
        storage = SummaryStorageService()
        deleted = storage.delete_summary(summary_id)
        
        if not deleted:
            raise HTTPException(status_code=404, detail="Summary not found")
        
        return {"message": "Summary deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))
