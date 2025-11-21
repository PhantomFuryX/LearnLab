import os
import json
import hashlib
from typing import Optional, Any, Union
from backend.utils.env_setup import get_logger

try:
    from redis import Redis
    HAS_REDIS = True
except ImportError:
    HAS_REDIS = False
    Redis = None

class CacheService:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(CacheService, cls).__new__(cls)
            cls._instance.initialized = False
        return cls._instance

    def __init__(self):
        if self.initialized:
            return
        
        self.logger = get_logger("CacheService")
        self.redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        self.redis = None
        self.enabled = False

        if HAS_REDIS:
            try:
                self.redis = Redis.from_url(self.redis_url, decode_responses=True)
                self.redis.ping()
                self.enabled = True
                self.logger.info(f"CacheService initialized with Redis at {self.redis_url}")
            except Exception as e:
                self.logger.error(f"Failed to connect to Redis: {e}")
                self.enabled = False
        else:
            self.logger.warning("Redis client not installed. Caching disabled.")
        
        self.default_ttl = int(os.getenv("CACHE_TTL", "3600"))  # Default 1 hour
        self.initialized = True

    def generate_key(self, *args, **kwargs) -> str:
        """Generate a deterministic cache key from arguments."""
        key_parts = [str(arg) for arg in args]
        # Sort kwargs to ensure deterministic order
        for k in sorted(kwargs.keys()):
            key_parts.append(f"{k}={kwargs[k]}")
        
        key_str = "|".join(key_parts)
        return hashlib.sha256(key_str.encode("utf-8")).hexdigest()

    def get(self, key: str) -> Optional[Any]:
        """Retrieve a value from the cache."""
        if not self.enabled or not self.redis:
            return None
        
        try:
            value = self.redis.get(key)
            if value:
                try:
                    return json.loads(value)
                except json.JSONDecodeError:
                    return value
            return None
        except Exception as e:
            self.logger.error(f"Cache get error for key {key}: {e}")
            return None

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set a value in the cache."""
        if not self.enabled or not self.redis:
            return False
        
        try:
            if isinstance(value, (dict, list, bool, int, float)):
                value_str = json.dumps(value)
            else:
                value_str = str(value)
            
            expiry = ttl if ttl is not None else self.default_ttl
            return bool(self.redis.set(key, value_str, ex=expiry))
        except Exception as e:
            self.logger.error(f"Cache set error for key {key}: {e}")
            return False

    def delete(self, key: str) -> bool:
        """Delete a value from the cache."""
        if not self.enabled or not self.redis:
            return False
        
        try:
            return bool(self.redis.delete(key))
        except Exception as e:
            self.logger.error(f"Cache delete error for key {key}: {e}")
            return False
