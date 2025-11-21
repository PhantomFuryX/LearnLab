from __future__ import annotations
import os, json, time, uuid
from typing import Dict, Optional
from backend.utils.env_setup import get_logger

class JobStore:
    def __init__(self, persist_dir: str) -> None:
        self.logger = get_logger("JobStore")
        self.path = os.path.join(persist_dir, "jobs.json")
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        if not os.path.exists(self.path):
            with open(self.path, "w", encoding="utf-8") as f:
                json.dump({"jobs": {}}, f)

    def _load(self) -> Dict:
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {"jobs": {}}

    def _save(self, data: Dict):
        tmp = self.path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f)
        os.replace(tmp, self.path)

    def create(self) -> str:
        jid = str(uuid.uuid4())
        data = self._load()
        data.setdefault("jobs", {})[jid] = {"status": "queued", "t": int(time.time()), "result": None}
        self._save(data)
        return jid

    def update(self, jid: str, status: str, result: Optional[Dict] = None):
        data = self._load()
        if jid in data.get("jobs", {}):
            data["jobs"][jid]["status"] = status
            if result is not None:
                data["jobs"][jid]["result"] = result
            data["jobs"][jid]["t"] = int(time.time())
            self._save(data)

    def get(self, jid: str) -> Optional[Dict]:
        data = self._load()
        return data.get("jobs", {}).get(jid)
