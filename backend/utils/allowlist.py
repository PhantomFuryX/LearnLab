from __future__ import annotations
import os, json, re
from typing import Dict, Any, List
from urllib.parse import urlparse

class Allowlist:
    def __init__(self, persist_dir: str) -> None:
        self.path = os.path.join(persist_dir, 'allowlist.json')
        os.makedirs(persist_dir, exist_ok=True)
        if not os.path.exists(self.path):
            with open(self.path, 'w', encoding='utf-8') as f:
                json.dump({"domains": [], "path_regex": ""}, f)

    def _load(self) -> Dict[str, Any]:
        try:
            with open(self.path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return {"domains": [], "path_regex": ""}

    def get(self) -> Dict[str, Any]:
        return self._load()

    def set(self, domains: List[str], path_regex: str) -> None:
        data = {"domains": [d.strip().lower() for d in domains if d.strip()], "path_regex": path_regex or ""}
        with open(self.path, 'w', encoding='utf-8') as f:
            json.dump(data, f)

    def is_allowed(self, url: str) -> bool:
        cfg = self._load()
        doms = cfg.get('domains') or []
        pat = cfg.get('path_regex') or ''
        try:
            if doms:
                host = urlparse(url).netloc.lower()
                ok = any(host == d or host.endswith('.'+d) for d in doms)
                if not ok:
                    return False
            if pat:
                path = urlparse(url).path or '/'
                if not re.search(pat, path):
                    return False
            return True
        except Exception:
            return True
