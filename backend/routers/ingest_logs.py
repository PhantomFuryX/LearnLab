from fastapi import APIRouter, HTTPException, Request
from typing import Optional
from backend.services.ingest_log_service import IngestLogService
from backend.services.rag_service import RAGService

router = APIRouter()
logs = IngestLogService()
rag = RAGService()

@router.get('/knowledge/ingests/recent')
async def recent_ingests(request: Request, limit: Optional[int] = 20):
    try:
        u = getattr(request.state, 'user', None)
        if not u or not u.get('id'):
            return {"items": []}
        items = logs.recent_ingests(u['id'], limit or 20)
        return {"items": items}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get('/knowledge/ingests/stats')
async def ingests_stats(request: Request):
    try:
        u = getattr(request.state, 'user', None)
        if not u or not u.get('id'):
            return {"namespaces": []}
        s = logs.stats_summary(u['id'])
        # stitch in registry counts
        reg = rag.registry
        if reg:
            ns_counts = {}
            for ns_row in s.get('namespaces', []):
                ns = ns_row['namespace']
                st = rag.stats(ns)
                ns_counts[ns] = st
            s['registry'] = ns_counts
        return s
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get('/knowledge/jobs/my')
async def my_jobs(request: Request, limit: Optional[int] = 20):
    try:
        u = getattr(request.state, 'user', None)
        if not u or not u.get('id'):
            return {"items": []}
        items = logs.user_jobs(u['id'], limit or 20)
        return {"items": items}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
