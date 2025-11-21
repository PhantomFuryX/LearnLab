from __future__ import annotations
import os, json
from typing import Dict
from urllib.parse import urlparse
from backend.utils.env_setup import get_logger

class DomainPolicy:
    def __init__(self, persist_dir: str) -> None:
        self.logger = get_logger("DomainPolicy")
        self.path = os.path.join(persist_dir, "domain_policies.json")
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        if not os.path.exists(self.path):
            with open(self.path, "w", encoding="utf-8") as f:
                json.dump({"policies": {}}, f)

    def _load(self) -> Dict:
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {"policies": {}}

    def get(self, url: str) -> Dict:
        data = self._load()
        host = urlparse(url).netloc.lower()
        p = data.get("policies", {}).get(host) or {}
        return {
            "min_interval_ms": int(p.get("min_interval_ms", 0)),
            "user_agent": p.get("user_agent"),
            "timeout": float(p.get("timeout", 20.0)),
        }

    def set(self, host: str, pol: Dict):
        data = self._load()
        data.setdefault("policies", {})[host.lower()] = pol
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(data, f)
