from __future__ import annotations
from typing import Any, Dict, Optional
import time
import os
import requests
from urllib import robotparser
from backend.utils.env_setup import get_logger
import os as _os
from backend.utils.tracing import span
from backend.utils.domain_policy import DomainPolicy

DEFAULT_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119 Safari/537.36"

class WebFetchTool:
    name = "web_fetch"

    def __init__(self) -> None:
        self.logger = get_logger("WebFetchTool")
        self._policy = DomainPolicy(_os.getenv("CHROMA_PERSIST_DIR", _os.getcwd()))
        try:
            rate = float(os.getenv("FETCH_RATE_PER_SEC", "0"))
            self._min_interval = 1.0 / rate if rate > 0 else 0.0
        except Exception:
            self._min_interval = 0.0
        self._last = 0.0

    def _throttle(self):
        if self._min_interval <= 0:
            return
        now = time.perf_counter()
        wait = self._min_interval - (now - self._last)
        if wait > 0:
            time.sleep(wait)
        self._last = time.perf_counter()

    def run(
        self,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        timeout: float = 20.0,
        respect_robots: bool = True,
        delay_ms: int = 0,
        max_retries: int = 1,
        backoff: float = 1.5,
        cond_etag: Optional[str] = None,
        cond_last_modified: Optional[str] = None,
    ) -> Dict[str, Any]:
        with span("tool.web_fetch", {"url": url}):
            h = {"User-Agent": DEFAULT_UA}
            if headers:
                h.update(headers)
            if cond_etag:
                h["If-None-Match"] = cond_etag
            if cond_last_modified:
                h["If-Modified-Since"] = cond_last_modified
            if respect_robots:
                try:
                    rp = robotparser.RobotFileParser()
                    from urllib.parse import urlparse, urljoin
                    p = urlparse(url)
                    robots_url = urljoin(f"{p.scheme}://{p.netloc}", "/robots.txt")
                    rp.set_url(robots_url)
                    rp.read()
                    if not rp.can_fetch(h["User-Agent"], url):
                        return {"error": "Disallowed by robots.txt", "url": url}
                except Exception:
                    pass
            if delay_ms > 0:
                time.sleep(delay_ms / 1000.0)
            attempt = 0
            while True:
                try:
                    self._throttle()
                    pol = self._policy.get(url)
                    if pol.get("user_agent"):
                        h["User-Agent"] = pol["user_agent"]
                    if pol.get("timeout"):
                        timeout = float(pol["timeout"]) or timeout
                    # merge min_interval
                    if pol.get("min_interval_ms"):
                        self._min_interval = max(self._min_interval, pol["min_interval_ms"]/1000.0)
                    resp = requests.get(url, headers=h, timeout=timeout)
                    if resp.status_code == 304:
                        return {"url": url, "status": 304, "not_modified": True, "headers": dict(resp.headers)}
                    resp.raise_for_status()
                    return {
                        "url": url,
                        "status": resp.status_code,
                        "headers": dict(resp.headers),
                        "text": resp.text,
                    }
                except Exception as e:
                    attempt += 1
                    if attempt > max_retries:
                        self.logger.error(f"WebFetch failed for {url}: {e}")
                        return {"error": str(e), "url": url}
                    time.sleep(backoff ** attempt)
