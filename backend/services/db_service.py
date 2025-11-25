import os
from typing import Optional
from pymongo import MongoClient

_client: Optional[MongoClient] = None
_db = None

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
MONGO_DB = os.getenv("MONGO_DB", "learnlab")
MONGO_DISABLED = os.getenv("MONGO_DISABLED", "false").lower() in ("1", "true", "yes")


class _NoOpCollection:
    """A minimal collection-like object returned when Mongo is disabled.
    It implements only the methods used at import-time (create_index) as no-ops.
    Other operations raise RuntimeError so tests must explicitly mock DB calls
    if they need to run without a real Mongo instance.
    """
    def create_index(self, *args, **kwargs):
        return None

    def insert_one(self, *args, **kwargs):
        raise RuntimeError("MongoDB is disabled in this environment")

    def find_one(self, *args, **kwargs):
        raise RuntimeError("MongoDB is disabled in this environment")

    def find(self, *args, **kwargs):
        raise RuntimeError("MongoDB is disabled in this environment")

    def delete_one(self, *args, **kwargs):
        raise RuntimeError("MongoDB is disabled in this environment")

    def delete_many(self, *args, **kwargs):
        raise RuntimeError("MongoDB is disabled in this environment")

    def update_one(self, *args, **kwargs):
        raise RuntimeError("MongoDB is disabled in this environment")


class _NoOpDB:
    def __getitem__(self, name: str):
        # return a no-op collection for any collection name
        return _NoOpCollection()


def get_db():
    """Return a MongoDB database object.

    If MONGO_DISABLED is set to true, return a no-op DB to avoid network
    calls during imports (useful for running tests that mock DB calls).
    """
    global _client, _db
    if MONGO_DISABLED:
        return _NoOpDB()

    if _db is not None:
        return _db

    # Lazily create the client. Note: MongoClient itself is lazy; network
    # I/O usually happens on the first operation (e.g. create_index). Tests
    # should avoid invoking DB ops at import time; services should guard
    # index creation if Mongo isn't available.
    _client = MongoClient(MONGO_URI)
    _db = _client[MONGO_DB]
    return _db
