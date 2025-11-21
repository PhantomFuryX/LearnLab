from fastapi import APIRouter, HTTPException, UploadFile, File, Form, BackgroundTasks, Response, Request
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from backend.core.agents.knowledge_agent import KnowledgeAgent
from backend.services.rag_service import RAGService
from backend.services.ingest_log_service import IngestLogService
import asyncio
from fastapi.responses import StreamingResponse
import uuid
from backend.utils.job_store import JobStore
from backend.utils.rq_jobs import enqueue_ingest_fetch, enqueue_ingest_sitemaps, get_job_status as rq_job_status
import os
import re
import time
from hashlib import sha256

router = APIRouter()
knowledge_agent = KnowledgeAgent()
rag_service = RAGService()
log_svc = IngestLogService()
job_store = JobStore(os.getenv("CHROMA_PERSIST_DIR", os.path.join(os.getcwd(), "chroma_data")))

# In-memory background job tracker (best effort, resets on restart)
JOBS: dict[str, dict] = {}

class KnowledgeRequest(BaseModel):
    payload: dict

class IngestRequest(BaseModel):
    namespace: str
    texts: List[str]
    metadatas: Optional[List[Dict[str, Any]]] = None
    ids: Optional[List[str]] = None
    chunk_size: Optional[int] = None
    chunk_overlap: Optional[int] = None
    mode: Optional[str] = None  # char | token | semantic

class IngestUrlsRequest(BaseModel):
    namespace: str
    urls: List[str]
    chunk_size: Optional[int] = None
    chunk_overlap: Optional[int] = None
    use_trafilatura: Optional[bool] = None
    mode: Optional[str] = None  # char | token | semantic

class IngestSitemapsRequest(BaseModel):
    namespace: str
    sitemap_urls: List[str]
    max_urls: int = 200
    same_domain_only: bool = True
    chunk_size: Optional[int] = None
    chunk_overlap: Optional[int] = None

class AskRequest(BaseModel):
    namespace: str
    question: str
    k: int = 4

# Tools and extractors
try:
    from backend.core.tools.web_fetch import WebFetchTool
    HAS_FETCH = True
except Exception:
    HAS_FETCH = False

try:
    import trafilatura
    HAS_TRAF = True
except Exception:
    HAS_TRAF = False

try:
    from bs4 import BeautifulSoup
    HAS_BS4 = True
except Exception:
    HAS_BS4 = False

class IngestFetchRequest(BaseModel):
    namespace: str
    urls: List[str]
    headers: Optional[Dict[str, str]] = None
    respect_robots: bool = True
    delay_ms: int = 0
    chunk_size: Optional[int] = None
    chunk_overlap: Optional[int] = None
    mode: Optional[str] = None  # char | token | semantic

class IngestFetchBgRequest(IngestFetchRequest):
    pass

class IngestSitemapsBgRequest(BaseModel):
    namespace: str
    sitemap_urls: List[str]
    max_urls: int = 200
    same_domain_only: bool = True
    chunk_size: Optional[int] = None
    chunk_overlap: Optional[int] = None

@router.post("/run")
async def run_knowledge(request: KnowledgeRequest):
    try:
        result = await knowledge_agent.handle(request.payload)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

def user_ns(req: Request, ns: str) -> str:
    u = getattr(req.state, 'user', None)
    if not u or not u.get('id'):
        return ns
    uid = u['id'][:8]
    return f"{uid}__{ns}"

def strip_user_prefix(req: Request, ns: str) -> str:
    u = getattr(req.state, 'user', None)
    if not u or not u.get('id'):
        return ns
    pfx = u['id'][:8] + "__"
    return ns[len(pfx):] if ns.startswith(pfx) else ns

@router.post("/ingest")
async def ingest_knowledge(request: IngestRequest, req: Request):
    try:
        res = rag_service.ingest_texts(
            namespace=user_ns(req, request.namespace),
            texts=request.texts,
            metadatas=request.metadatas,
            ids=request.ids,
            chunk_size=request.chunk_size,
            chunk_overlap=request.chunk_overlap,
            mode=request.mode,
        )
        try:
            u = getattr(req.state, 'user', None)
            if u and u.get('id'):
                log_svc.log_ingest(u['id'], user_ns(req, request.namespace), 'texts', request.ids or [], res.get('count', 0))
        except Exception:
            pass
        return res
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/ingest_urls")
async def ingest_urls(request: IngestUrlsRequest, req: Request):
    try:
        res = rag_service.ingest_urls(
            namespace=user_ns(req, request.namespace), 
            urls=request.urls,
            chunk_size=request.chunk_size,
            chunk_overlap=request.chunk_overlap,
            use_trafilatura=request.use_trafilatura,
            mode=request.mode,
        )
        try:
            u = getattr(req.state, 'user', None)
            if u and u.get('id'):
                log_svc.log_ingest(u['id'], user_ns(req, request.namespace), 'urls', request.urls, res.get('count', 0))
        except Exception:
            pass
        return res
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/ingest_sitemaps")
async def ingest_sitemaps(request: IngestSitemapsRequest, req: Request):
    try:
        res = rag_service.ingest_sitemaps(
            namespace=user_ns(req, request.namespace),
            sitemap_urls=request.sitemap_urls,
            max_urls=request.max_urls,
            same_domain_only=request.same_domain_only,
            chunk_size=request.chunk_size,
            chunk_overlap=request.chunk_overlap,
        )
        return res
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/ingest_files")
async def ingest_files(
    namespace: str = Form(...),
    files: List[UploadFile] = File(...),
    chunk_size: Optional[int] = Form(None),
    chunk_overlap: Optional[int] = Form(None),
    mode: Optional[str] = Form(None),  # char | token | semantic
    req: Request = None
):
    try:
        file_blobs = []
        for f in files:
            content = await f.read()
            file_blobs.append((f.filename, content))
        ns = user_ns(req, namespace) if req else namespace
        res = rag_service.ingest_files(
            namespace=ns,
            files=file_blobs,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            mode=mode,
        )
        try:
            u = getattr(req.state, 'user', None)
            if u and u.get('id'):
                sources = [f for f,_ in file_blobs]
                log_svc.log_ingest(u['id'], ns, 'files', sources, res.get('count', 0))
        except Exception:
            pass
        return res
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/ask")
async def ask_knowledge(request: AskRequest, req: Request):
    try:
        res = await rag_service.answer_question(
            namespace=user_ns(req, request.namespace),
            question=request.question,
            k=request.k,
        )
        return res
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/ingest_fetch")
async def ingest_fetch(request: IngestFetchRequest, response: Response):
    if not HAS_FETCH:
        raise HTTPException(status_code=400, detail="WebFetchTool not available")
    try:
        rid = str(uuid.uuid4())
        fetch = WebFetchTool()
        texts: List[str] = []
        metas: List[Dict[str, Any]] = []
        ids: List[str] = []
        allow = os.getenv("RAG_URL_ALLOWLIST", "").strip()
        allow_domains = [d.strip().lower() for d in allow.split(",") if d.strip()]
        path_pat = os.getenv("RAG_URL_PATH_ALLOWLIST", "").strip()
        compiled_pat = re.compile(path_pat) if path_pat else None
        def allowed(u: str) -> bool:
            ok_domain = True
            if allow_domains:
                try:
                    from urllib.parse import urlparse
                    host = urlparse(u).netloc.lower()
                    ok_domain = any(host == d or host.endswith("." + d) for d in allow_domains)
                except Exception:
                    ok_domain = True
            if not ok_domain:
                return False
            if compiled_pat:
                try:
                    from urllib.parse import urlparse
                    path = urlparse(u).path or "/"
                    if not compiled_pat.search(path):
                        return False
                except Exception:
                    return True
            return True
        for u in request.urls:
            if not allowed(u):
                continue
            cond_etag = None
            cond_lastmod = None
            if getattr(rag_service, 'registry', None):
                ns = rag_service._sanitize_namespace(request.namespace)
                prev = rag_service.registry.get_url_meta(ns, u)
                if prev:
                    cond_etag = prev.get("etag")
                    cond_lastmod = prev.get("last_modified")
            res = fetch.run(u, headers=request.headers, respect_robots=request.respect_robots, delay_ms=request.delay_ms, cond_etag=cond_etag, cond_last_modified=cond_lastmod)
            if res.get("error") or res.get("not_modified"):
                continue
            html = res.get("text", "")
            text = None
            if HAS_TRAF:
                try:
                    text = trafilatura.extract(html)
                except Exception:
                    text = None
            if not text and HAS_BS4:
                try:
                    soup = BeautifulSoup(html, "html.parser")
                    for t in soup(["script", "style", "noscript"]):
                        t.decompose()
                    text = soup.get_text(separator=" ", strip=True)
                except Exception:
                    text = None
            if not text:
                continue
            try:
                if getattr(rag_service, 'registry', None):
                    ns = rag_service._sanitize_namespace(request.namespace)
                    url_hash = sha256(text.encode("utf-8", errors="ignore")).hexdigest()
                    rag_service.registry.set_url_meta(ns, u, {
                        "hash": url_hash,
                        "last_modified": (res.get("headers") or {}).get("Last-Modified"),
                        "etag": (res.get("headers") or {}).get("ETag"),
                        "t": int(time.time()),
                    })
            except Exception:
                pass
            texts.append(text)
            metas.append({"source": u, "content_type": (res.get("headers") or {}).get("Content-Type")})
            ids.append(u)
        if not texts:
            response.headers["X-Request-ID"] = rid
            return {"request_id": rid, "namespace": request.namespace, "count": 0, "ids": []}
        ns_used = request.namespace
        out = rag_service.ingest_texts(
            namespace=ns_used,
            texts=texts,
            metadatas=metas,
            ids=ids,
            chunk_size=request.chunk_size,
            chunk_overlap=request.chunk_overlap,
        )
        try:
            # Log fetch ingest
            uid = None
            if uid:
                log_svc.log_ingest(uid, ns_used, 'fetch', ids, out.get('count', 0))
        except Exception:
            pass
        response.headers["X-Request-ID"] = rid
        out["request_id"] = rid
        return out
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Background job variants with persistent JobStore
@router.post("/ingest_fetch_bg")
async def ingest_fetch_bg(request: IngestFetchBgRequest, background: BackgroundTasks, req: Request):
    # Prefer Redis/RQ when available
    try:
        jid = enqueue_ingest_fetch(user_ns(req, request.namespace), request.urls, headers=request.headers or {}, respect_robots=request.respect_robots, delay_ms=request.delay_ms, chunk_size=request.chunk_size, chunk_overlap=request.chunk_overlap)
        try:
            u = getattr(req.state, 'user', None)
            if u and u.get('id'):
                log_svc.log_job(u['id'], 'fetch_bg', {"urls": request.urls, "namespace": user_ns(req, request.namespace)}, 'rq', jid, 'queued')
        except Exception:
            pass
        return {"job_id": jid, "status": "queued", "backend": "rq"}
    except Exception:
        # Fallback to local JobStore
        jid = job_store.create()
        def _run():
            try:
                job_store.update(jid, "running")
                # local fallback uses direct function
                res = rag_service.ingest_texts(namespace=user_ns(req, request.namespace), texts=[], metadatas=[], ids=[])
                job_store.update(jid, "done", res)
            except Exception as e:
                job_store.update(jid, "error", {"error": str(e)})
        background.add_task(_run)
        return {"job_id": jid, "status": "queued", "backend": "local"}

@router.post("/ingest_sitemaps_bg")
async def ingest_sitemaps_bg(request: IngestSitemapsBgRequest, background: BackgroundTasks, req: Request):
    try:
        jid = enqueue_ingest_sitemaps(user_ns(req, request.namespace), request.sitemap_urls, max_urls=request.max_urls, same_domain_only=request.same_domain_only, chunk_size=request.chunk_size, chunk_overlap=request.chunk_overlap)
        try:
            u = getattr(req.state, 'user', None)
            if u and u.get('id'):
                log_svc.log_job(u['id'], 'sitemaps_bg', {"sitemap_urls": request.sitemap_urls, "namespace": user_ns(req, request.namespace)}, 'rq', jid, 'queued')
        except Exception:
            pass
        return {"job_id": jid, "status": "queued", "backend": "rq"}
    except Exception:
        jid = job_store.create()
        def _run():
            try:
                job_store.update(jid, "running")
                res = rag_service.ingest_sitemaps(
                    namespace=user_ns(req, request.namespace),
                    sitemap_urls=request.sitemap_urls,
                    max_urls=request.max_urls,
                    same_domain_only=request.same_domain_only,
                    chunk_size=request.chunk_size,
                    chunk_overlap=request.chunk_overlap,
                )
                job_store.update(jid, "done", res)
            except Exception as e:
                job_store.update(jid, "error", {"error": str(e)})
        background.add_task(_run)
        return {"job_id": jid, "status": "queued", "backend": "local"}

@router.get("/jobs")
async def list_jobs(req: Request, limit: int = 20):
    try:
        u = getattr(req.state, 'user', None)
        if not u or not u.get('id'):
            # If no auth, return empty or 401? For now, empty list to be safe
            return {"jobs": []}
        
        jobs = log_svc.user_jobs(u['id'], limit=limit)
        
        # Enrich with live status from Redis if possible
        for job in jobs:
            try:
                # Only check live status for active jobs to save Redis calls
                if job.get("status") in ["queued", "running", "started"]:
                    live = rq_job_status(job["job_id"])
                    if live and not live.get("error"):
                        job["status"] = live.get("status", job["status"])
                        if live.get("result"):
                            job["result"] = live["result"]
            except Exception:
                pass
                
        return {"jobs": jobs}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/jobs/{job_id}")
async def get_job_status(job_id: str):
    # Try Redis first
    try:
        s = rq_job_status(job_id)
        if s and not s.get("error"):
            return s
    except Exception:
        pass
    # Fallback to local store
    job = job_store.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="job not found")
    return {"id": job_id, **job}

# ---- Namespace management ----
@router.get("/namespaces")
async def list_namespaces(response: Response, req: Request):
    try:
        rid = req.headers.get("X-Request-ID") or str(uuid.uuid4())
        all_ns = rag_service.list_namespaces()
        u = getattr(req.state, 'user', None)
        if u and u.get('id'):
            pfx = u['id'][:8] + "__"
            user_ns_list = [strip_user_prefix(req, ns) for ns in all_ns if ns.startswith(pfx)]
        else:
            user_ns_list = []
        response.headers["X-Request-ID"] = rid
        return {"request_id": rid, "namespaces": user_ns_list}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/stats/{namespace}")
async def stats_namespace(namespace: str, response: Response, req: Request):
    try:
        rid = req.headers.get("X-Request-ID") or str(uuid.uuid4())
        response.headers["X-Request-ID"] = rid
        out = rag_service.stats(user_ns(req, namespace))
        out["request_id"] = rid
        return out
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/namespaces/{namespace}")
async def delete_namespace(namespace: str, response: Response, req: Request):
    try:
        rid = req.headers.get("X-Request-ID") or str(uuid.uuid4())
        response.headers["X-Request-ID"] = rid
        out = rag_service.delete_namespace(user_ns(req, namespace))
        out["request_id"] = rid
        return out
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
