import os
from typing import Optional
from pymongo import MongoClient

_client: Optional[MongoClient] = None
_db = None

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
MONGO_DB = os.getenv("MONGO_DB", "learnlab")

def get_db():
    global _client, _db
    if _db is not None:
        return _db
    _client = MongoClient(MONGO_URI)
    _db = _client[MONGO_DB]
    return _db
