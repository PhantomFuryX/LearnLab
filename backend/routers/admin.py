from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List
import os
from backend.utils.domain_policy import DomainPolicy
from backend.utils.allowlist import Allowlist
from rq import Queue  # type: ignore
from redis import Redis  # type: ignore
from rq.registry import FailedJobRegistry  # type: ignore
HAS_RQ = True

REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
RQ_QUEUE = os.getenv('RQ_QUEUE', 'learnlab')

router = APIRouter()

class DomainPolicySet(BaseModel):
    host: str
    min_interval_ms: int | None = None
    user_agent: str | None = None
    timeout: float | None = None

@router.get('/domain_policy/{host}')
async def get_domain_policy(host: str):
    dp = DomainPolicy(os.getenv('CHROMA_PERSIST_DIR', os.getcwd()))
    return dp.get(f'https://{host}/')

@router.put('/domain_policy')
async def put_domain_policy(body: DomainPolicySet):
    dp = DomainPolicy(os.getenv('CHROMA_PERSIST_DIR', os.getcwd()))
    pol = {}
    if body.min_interval_ms is not None: pol['min_interval_ms'] = int(body.min_interval_ms)
    if body.user_agent: pol['user_agent'] = body.user_agent
    if body.timeout is not None: pol['timeout'] = float(body.timeout)
    dp.set(body.host, pol)
    return {"ok": True}

class AllowlistSet(BaseModel):
    domains: List[str] = []
    path_regex: str = ''

@router.get('/allowlist')
async def get_allowlist():
    al = Allowlist(os.getenv('CHROMA_PERSIST_DIR', os.getcwd()))
    return al.get()

@router.put('/allowlist')
async def put_allowlist(body: AllowlistSet):
    al = Allowlist(os.getenv('CHROMA_PERSIST_DIR', os.getcwd()))
    al.set(body.domains, body.path_regex)
    return {"ok": True}

@router.get('/jobs/failed')
async def list_failed_jobs():
    if not HAS_RQ:
        return {"error": "RQ not available"}
    conn = Redis.from_url(REDIS_URL)
    q = Queue(RQ_QUEUE, connection=conn)
    reg = FailedJobRegistry(queue=q)
    ids = reg.get_job_ids()
    return {"failed_job_ids": ids}

@router.post('/jobs/requeue/{job_id}')
async def requeue_failed_job(job_id: str):
    if not HAS_RQ:
        return {"error": "RQ not available"}
    from rq.job import Job  # type: ignore
    conn = Redis.from_url(REDIS_URL)
    q = Queue(RQ_QUEUE, connection=conn)
    reg = FailedJobRegistry(queue=q)
    try:
        job = Job.fetch(job_id, connection=conn)
        if job_id in reg.get_job_ids():
            job.requeue()
            return {"ok": True}
        else:
            raise HTTPException(status_code=404, detail="job not in failed registry")
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))
