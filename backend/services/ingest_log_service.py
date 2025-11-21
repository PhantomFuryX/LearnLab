from __future__ import annotations
import time
from typing import List, Dict, Any, Optional
from bson import ObjectId
from backend.services.db_service import get_db
from backend.utils.env_setup import get_logger

class IngestLogService:
    def __init__(self) -> None:
        self.logger = get_logger("IngestLogService")
        self.db = get_db()
        self.col = self.db["ingests"]
        self.jobs = self.db["jobs"]
        self.col.create_index([("user_id", 1), ("created_at", -1)])
        self.col.create_index([("namespace", 1)])
        self.jobs.create_index([("user_id", 1), ("created_at", -1)])
        self.jobs.create_index([("job_id", 1)], unique=True)

    def log_ingest(self, user_id: str, namespace: str, typ: str, sources: List[str], count: int) -> None:
        now = int(time.time())
        try:
            doc = {
                "user_id": ObjectId(user_id) if ObjectId.is_valid(user_id) else user_id,
                "namespace": namespace,
                "type": typ,
                "sources": sources[:50],
                "count": int(count),
                "created_at": now,
            }
            self.col.insert_one(doc)
        except Exception as e:
            self.logger.error(f"log_ingest failed: {e}")

    def recent_ingests(self, user_id: str, limit: int = 20) -> List[Dict[str, Any]]:
        cur = self.col.find({"user_id": ObjectId(user_id) if ObjectId.is_valid(user_id) else user_id}).sort("created_at", -1).limit(int(limit))
        items = []
        for d in cur:
            d["id"] = str(d.pop("_id", ""))
            if isinstance(d.get("user_id"), ObjectId):
                d["user_id"] = str(d["user_id"])
            items.append(d)
        return items

    def stats_summary(self, user_id: str) -> Dict[str, Any]:
        # Basic per-namespace counts from logs for now; RAG registry can be stitched in by API handler
        pipeline = [
            {"$match": {"user_id": ObjectId(user_id) if ObjectId.is_valid(user_id) else user_id}},
            {"$group": {"_id": "$namespace", "events": {"$sum": 1}, "total_count": {"$sum": "$count"}}},
            {"$sort": {"events": -1}},
            {"$limit": 100},
        ]
        rows = list(self.col.aggregate(pipeline))
        out = []
        for r in rows:
            out.append({"namespace": r.get("_id"), "events": r.get("events", 0), "logged_total": r.get("total_count", 0)})
        return {"namespaces": out}

    def log_job(self, user_id: str, typ: str, payload: Dict[str, Any], backend: str, job_id: str, status: str = "queued") -> None:
        now = int(time.time())
        try:
            doc = {
                "user_id": ObjectId(user_id) if ObjectId.is_valid(user_id) else user_id,
                "type": typ,
                "payload": payload,
                "backend": backend,
                "job_id": job_id,
                "status": status,
                "created_at": now,
            }
            self.jobs.insert_one(doc)
        except Exception as e:
            self.logger.error(f"log_job failed: {e}")

    def user_jobs(self, user_id: str, limit: int = 20) -> List[Dict[str, Any]]:
        cur = self.jobs.find({"user_id": ObjectId(user_id) if ObjectId.is_valid(user_id) else user_id}).sort("created_at", -1).limit(int(limit))
        items = []
        for d in cur:
            d["id"] = str(d.pop("_id", ""))
            if isinstance(d.get("user_id"), ObjectId):
                d["user_id"] = str(d["user_id"])
            items.append(d)
        return items

    def update_job_status(self, job_id: str, status: str, result_summary: Optional[Dict[str, Any]] = None) -> None:
        try:
            upd = {"$set": {"status": status}}
            if result_summary is not None:
                upd["$set"]["result"] = result_summary
            self.jobs.update_one({"job_id": job_id}, upd, upsert=False)
        except Exception as e:
            self.logger.error(f"update_job_status failed: {e}")
