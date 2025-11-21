from __future__ import annotations
import os, json, time, shutil
from typing import Dict, List, Optional
from backend.utils.env_setup import get_logger

SCHEMA_VERSION = 1

class NamespaceRegistry:
    def __init__(self, persist_dir: str) -> None:
        self.logger = get_logger("NamespaceRegistry")
        self.persist_dir = persist_dir
        self.path = os.path.join(self.persist_dir, "namespaces.json")
        os.makedirs(self.persist_dir, exist_ok=True)
        if not os.path.exists(self.path):
            with open(self.path, "w", encoding="utf-8") as f:
                json.dump({"schema": SCHEMA_VERSION, "namespaces": {}}, f)

    def _load(self) -> Dict:
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if "namespaces" not in data:
                    data = {"schema": SCHEMA_VERSION, "namespaces": {}}
                return data
        except Exception:
            return {"schema": SCHEMA_VERSION, "namespaces": {}}

    def _save(self, data: Dict) -> None:
        tmp = self.path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f)
        os.replace(tmp, self.path)

    def register(self, namespace: str, added: int = 0) -> None:
        data = self._load()
        ns = data.setdefault("namespaces", {}).setdefault(namespace, {
            "total_added": 0,
            "chunk_count": 0,
            "last_updated": 0,
            "hashes": {},           # content_hash -> 1 (namespace scope)
            "hashes_global": {},    # optional global across namespaces (shadow)
            "hashes_by_source": {}, # source_id -> {hash:1}
            "urls": {},             # url -> {hash, last_modified, etag, t}
            "sources": {},          # source_id -> {added:int,last_updated:int}
        })
        ns["total_added"] = int(ns.get("total_added", 0)) + int(added)
        ns["chunk_count"] = int(ns.get("chunk_count", 0)) + int(added)
        ns["last_updated"] = int(time.time())
        self._save(data)

    def add_hashes(self, namespace: str, hashes: List[str]) -> None:
        if not hashes:
            return
        data = self._load()
        ns = data.setdefault("namespaces", {}).setdefault(namespace, {
            "total_added": 0, "chunk_count": 0, "last_updated": 0, "hashes": {}, "hashes_global": {}, "hashes_by_source": {}, "urls": {}, "sources": {}
        })
        for h in hashes:
            ns.setdefault("hashes", {})[h] = 1
        ns["last_updated"] = int(time.time())
        self._save(data)

    def add_source_hashes(self, namespace: str, source_id: str, hashes: List[str]) -> None:
        if not hashes:
            return
        data = self._load()
        ns = data.setdefault("namespaces", {}).setdefault(namespace, {
            "total_added": 0, "chunk_count": 0, "last_updated": 0, "hashes": {}, "hashes_global": {}, "hashes_by_source": {}, "urls": {}, "sources": {}
        })
        src = ns.setdefault("hashes_by_source", {}).setdefault(source_id, {})
        for h in hashes:
            src[h] = 1
            ns.setdefault("hashes_global", {})[h] = 1
        s = ns.setdefault("sources", {}).setdefault(source_id, {"added": 0, "last_updated": 0})
        s["added"] += len(hashes)
        s["last_updated"] = int(time.time())
        ns["last_updated"] = int(time.time())
        self._save(data)

    def has_hash(self, namespace: str, h: str) -> bool:
        data = self._load()
        return bool(data.get("namespaces", {}).get(namespace, {}).get("hashes", {}).get(h))

    def has_hash_global(self, namespace: str, h: str) -> bool:
        data = self._load()
        return bool(data.get("namespaces", {}).get(namespace, {}).get("hashes_global", {}).get(h))

    def has_source_hash(self, namespace: str, source_id: str, h: str) -> bool:
        data = self._load()
        return bool(data.get("namespaces", {}).get(namespace, {}).get("hashes_by_source", {}).get(source_id, {}).get(h))

    def get_url_meta(self, namespace: str, url: str) -> Optional[Dict]:
        data = self._load()
        return data.get("namespaces", {}).get(namespace, {}).get("urls", {}).get(url)

    def set_url_meta(self, namespace: str, url: str, meta: Dict) -> None:
        data = self._load()
        ns = data.setdefault("namespaces", {}).setdefault(namespace, {
            "total_added": 0, "chunk_count": 0, "last_updated": 0, "hashes": {}, "urls": {}
        })
        ns.setdefault("urls", {})[url] = meta
        ns["last_updated"] = int(time.time())
        self._save(data)

    def list_namespaces(self) -> List[str]:
        data = self._load()
        return sorted(list(data.get("namespaces", {}).keys()))

    def stats(self, namespace: str) -> Dict:
        data = self._load()
        ns = data.get("namespaces", {}).get(namespace, {})
        if not ns:
            return {"namespace": namespace, "exists": False}
        return {
            "namespace": namespace,
            "exists": True,
            "chunk_count": ns.get("chunk_count", 0),
            "total_added": ns.get("total_added", 0),
            "last_updated": ns.get("last_updated", 0),
            "url_count": len(ns.get("urls", {})),
            "hash_count": len(ns.get("hashes", {})),
            "source_count": len(ns.get("sources", {})),
            "sources": ns.get("sources", {}),
        }

    def remove(self, namespace: str) -> None:
        data = self._load()
        if namespace in data.get("namespaces", {}):
            del data["namespaces"][namespace]
            self._save(data)
        # Remove blob directory if exists
        blob_dir = os.path.join(self.persist_dir, "blobs", namespace)
        try:
            if os.path.isdir(blob_dir):
                shutil.rmtree(blob_dir)
        except Exception:
            pass

    def reset(self, namespace: str) -> None:
        # Same as remove for now
        self.remove(namespace)
