from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from backend.core.agents.post_agent import PostAgent
from backend.services.db_service import get_db

router = APIRouter()
agent = PostAgent()
db = get_db()

class PostGenerateRequest(BaseModel):
    content: str
    platform: str = "linkedin"
    tone: str = "professional"

class PostPublishRequest(BaseModel):
    post_data: Dict[str, Any]

@router.post("/generate")
async def generate_post(req: PostGenerateRequest):
    try:
        res = await agent.generate_post(req.content, req.platform, req.tone)
        return res
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/publish")
async def publish_post(req: PostPublishRequest):
    try:
        res = await agent.publish_post(req.post_data)
        return res
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/history")
async def get_history(limit: int = 20):
    try:
        cursor = db["posts"].find().sort("created_at", -1).limit(limit)
        posts = []
        for doc in cursor:
            doc["_id"] = str(doc["_id"])
            posts.append(doc)
        return {"history": posts}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
