from __future__ import annotations
import os, json, time
from typing import Dict, List
from backend.utils.env_setup import get_logger
try:
    from redis import Redis  # type: ignore
    HAS_REDIS = True
except Exception:
    HAS_REDIS = False

class GlobalRegistry:
    def __init__(self, persist_dir: str) -> None:
        self.logger = get_logger("GlobalRegistry")
        self.redis_url = os.getenv("REDIS_URL")
        self.redis = None
        if HAS_REDIS and self.redis_url:
            try:
                self.redis = Redis.from_url(self.redis_url)
            except Exception as e:
                self.logger.error(f"Redis unavailable: {e}")
                self.redis = None
        self.path = os.path.join(persist_dir, "global_hashes.json")
        os.makedirs(persist_dir, exist_ok=True)
        if not self.redis and not os.path.exists(self.path):
            with open(self.path, "w", encoding="utf-8") as f:
                json.dump({"schema": 1, "hashes": {}, "last_updated": int(time.time())}, f)

    def _load(self) -> Dict:
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {"schema": 1, "hashes": {}, "last_updated": 0}

    def _save(self, data: Dict) -> None:
        tmp = self.path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f)
        os.replace(tmp, self.path)

    def has_hash(self, h: str) -> bool:
        if self.redis:
            try:
                return bool(self.redis.sismember("global_hashes", h))
            except Exception:
                pass
        data = self._load()
        return bool(data.get("hashes", {}).get(h))

    def add_hashes(self, hashes: List[str]) -> None:
        if not hashes:
            return
        if self.redis:
            try:
                self.redis.sadd("global_hashes", *hashes)
                return
            except Exception:
                pass
        data = self._load()
        for h in hashes:
            data.setdefault("hashes", {})[h] = 1
        data["last_updated"] = int(time.time())
        self._save(data)
