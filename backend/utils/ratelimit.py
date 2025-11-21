import asyncio
import time
from typing import Optional

class AsyncRateLimiter:
    """Simple async rate limiter. Ensures at most `rate_per_sec` operations per second.
    Uses a minimal sleep based on last-acquire timestamp.
    """
    def __init__(self, rate_per_sec: float) -> None:
        self.rate = float(rate_per_sec) if rate_per_sec and rate_per_sec > 0 else 0.0
        self._min_interval = 1.0 / self.rate if self.rate > 0 else 0.0
        self._last: float = 0.0
        self._lock = asyncio.Lock()

    async def acquire(self):
        if self._min_interval <= 0:
            return
        async with self._lock:
            now = time.perf_counter()
            wait = self._min_interval - (now - self._last)
            if wait > 0:
                await asyncio.sleep(wait)
            self._last = time.perf_counter()
