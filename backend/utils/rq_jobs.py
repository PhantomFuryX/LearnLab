from __future__ import annotations
import os
from typing import Dict, Any, List

try:
    from rq import Queue, Retry  # type: ignore
    from redis import Redis  # type: ignore
    HAS_RQ = True
except Exception:
    HAS_RQ = False
    Queue = None  # type: ignore
    Redis = None  # type: ignore
    Retry = None  # type: ignore

from backend.services.rag_service import RAGService

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
QUEUE_NAME = os.getenv("RQ_QUEUE", "learnlab")

_redis = None
_queue = None

def _get_queue():
    global _redis, _queue
    if not HAS_RQ:
        return None
    if _queue is None:
        _redis = Redis.from_url(REDIS_URL)
        _queue = Queue(QUEUE_NAME, connection=_redis)
    return _queue

# ---- Job functions (run in worker) ----

def job_ingest_fetch(namespace: str, urls: List[str], headers: Dict[str, str] | None = None, respect_robots: bool = True, delay_ms: int = 0, chunk_size: int | None = None, chunk_overlap: int | None = None) -> Dict[str, Any]:
    svc = RAGService()
    # Reuse WebFetchTool path: we mimic /ingest_fetch handler logic here with simple requests
    from backend.core.tools.web_fetch import WebFetchTool
    texts: List[str] = []
    metas: List[Dict[str, Any]] = []
    ids: List[str] = []
    fetch = WebFetchTool()
    for u in urls:
        res = fetch.run(u, headers=headers or {}, respect_robots=respect_robots, delay_ms=delay_ms)
        if res.get("error") or res.get("not_modified"):
            continue
        html = res.get("text", "")
        text = None
        try:
            import trafilatura  # type: ignore
            text = trafilatura.extract(html)
        except Exception:
            text = None
        if not text:
            try:
                from bs4 import BeautifulSoup  # type: ignore
                soup = BeautifulSoup(html, "html.parser")
                for t in soup(["script", "style", "noscript"]):
                    t.decompose()
                text = soup.get_text(separator=" ", strip=True)
            except Exception:
                text = None
        if not text:
            continue
        texts.append(text)
        metas.append({"source": u, "content_type": (res.get("headers") or {}).get("Content-Type")})
        ids.append(u)
    if not texts:
        return {"namespace": namespace, "count": 0, "ids": []}
    return svc.ingest_texts(namespace, texts, metas, ids, chunk_size=chunk_size, chunk_overlap=chunk_overlap)


def job_ingest_sitemaps(namespace: str, sitemap_urls: List[str], max_urls: int = 200, same_domain_only: bool = True, chunk_size: int | None = None, chunk_overlap: int | None = None) -> Dict[str, Any]:
    svc = RAGService()
    return svc.ingest_sitemaps(namespace=namespace, sitemap_urls=sitemap_urls, max_urls=max_urls, same_domain_only=same_domain_only, chunk_size=chunk_size, chunk_overlap=chunk_overlap)

# ---- Enqueue helpers ----

def enqueue_ingest_fetch(*args, **kwargs):
    q = _get_queue()
    if q is None:
        raise RuntimeError("RQ/Redis not available")
    retry = Retry(max=3, interval=[60, 300, 600]) if Retry else None
    job = q.enqueue(job_ingest_fetch, *args, **kwargs, retry=retry, job_timeout=1800, failure_ttl=86400)
    return job.get_id()

def enqueue_ingest_sitemaps(*args, **kwargs):
    q = _get_queue()
    if q is None:
        raise RuntimeError("RQ/Redis not available")
    retry = Retry(max=3, interval=[60, 300, 600]) if Retry else None
    job = q.enqueue(job_ingest_sitemaps, *args, **kwargs, retry=retry, job_timeout=1800, failure_ttl=86400)
    return job.get_id()


def get_job_status(job_id: str) -> Dict[str, Any]:
    if not HAS_RQ:
        return {"error": "RQ not available"}
    from rq.job import Job  # type: ignore
    conn = Redis.from_url(REDIS_URL)
    try:
        job = Job.fetch(job_id, connection=conn)
    except Exception:
        return {"error": "job not found"}
    data: Dict[str, Any] = {"id": job_id, "status": job.get_status()}
    if job.is_finished:
        data["result"] = job.result
    if job.is_failed:
        data["exc_info"] = job.exc_info
    return data
