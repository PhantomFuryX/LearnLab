import time
from fastapi import Request, HTTPException
from typing import Dict, Tuple
import os

RATE_LIMIT_RPM = int(float(os.getenv("RATE_LIMIT_RPM", "0")))

class RateLimiter:
    def __init__(self, rpm: int) -> None:
        self.rpm = rpm
        self.buckets: Dict[str, Tuple[int, float]] = {}  # key -> (tokens, reset_time)

    def check(self, key: str):
        if self.rpm <= 0:
            return
        now = time.time()
        tokens, reset = self.buckets.get(key, (self.rpm, now + 60))
        if now > reset:
            tokens = self.rpm
            reset = now + 60
        if tokens <= 0:
            raise HTTPException(status_code=429, detail="Too Many Requests")
        self.buckets[key] = (tokens - 1, reset)

rl = RateLimiter(RATE_LIMIT_RPM)

async def rate_limit_middleware(request: Request, call_next):
    try:
        if RATE_LIMIT_RPM > 0:
            ip = request.client.host if request.client else "unknown"
            rl.check(ip)
    except HTTPException as e:
        raise e
    return await call_next(request)
