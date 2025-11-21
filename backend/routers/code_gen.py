"""
Code Generation API endpoints
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from backend.core.agents.code_agent import CodeAgent
from backend.services.code_storage_service import CodeStorageService
from backend.services.summary_storage_service import SummaryStorageService
from backend.utils.env_setup import get_logger

router = APIRouter()
logger = get_logger()

class CodeGenRequest(BaseModel):
    summary_id: str  # ID of summary to generate code from
    stack: str = "langchain"  # langchain, pytorch, tensorflow, vanilla
    language: str = "python"
    max_examples: int = 3  # Generate code for top N summaries


@router.post("/from-summary/{summary_id}")
async def generate_code_from_summary(
    summary_id: str,
    stack: str = "langchain",
    language: str = "python",
    max_examples: int = 3
):
    """
    Generate code examples from a summary.
    
    Example: POST /code/from-summary/abc-123?stack=langchain&language=python&max_examples=3
    """
    try:
        # Get summary
        summary_storage = SummaryStorageService()
        summary_doc = summary_storage.get_summary(summary_id)
        
        if not summary_doc:
            raise HTTPException(status_code=404, detail="Summary not found")
        
        summaries = summary_doc.get("summaries", [])
        if not summaries:
            raise HTTPException(status_code=400, detail="No summaries to generate code from")
        
        # Generate code
        agent = CodeAgent()
        code_examples = await agent.generate_multiple(
            summaries=summaries,
            stack=stack,
            language=language,
            limit=max_examples
        )
        
        # Store code
        code_storage = CodeStorageService()
        code_id = code_storage.store_code(
            summary_id=summary_id,
            query=summary_doc.get("query", ""),
            code_examples=code_examples,
            stack=stack,
            language=language,
            namespace=summary_doc.get("namespace", "default")
        )
        
        return {
            "code_id": code_id,
            "summary_id": summary_id,
            "code_examples": code_examples,
            "total": len(code_examples),
            "stack": stack,
            "language": language
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Code generation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/list")
async def list_code_examples(
    namespace: Optional[str] = None,
    stack: Optional[str] = None,
    language: Optional[str] = None,
    limit: int = 50,
    skip: int = 0
):
    """List generated code examples with filters."""
    try:
        storage = CodeStorageService()
        code_list = storage.list_code(
            namespace=namespace,
            stack=stack,
            language=language,
            limit=limit,
            skip=skip
        )
        return {"code_examples": code_list, "count": len(code_list)}
    except Exception as e:
        logger.error(f"Failed to list code: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{code_id}")
async def get_code_example(code_id: str):
    """Get specific code collection by ID."""
    try:
        storage = CodeStorageService()
        code = storage.get_code(code_id)
        
        if not code:
            raise HTTPException(status_code=404, detail="Code not found")
        
        return code
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get code: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{code_id}")
async def delete_code(code_id: str):
    """Delete code collection."""
    try:
        storage = CodeStorageService()
        deleted = storage.delete_code(code_id)
        
        if not deleted:
            raise HTTPException(status_code=404, detail="Code not found")
        
        return {"message": "Code deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete code: {e}")
        raise HTTPException(status_code=500, detail=str(e))
