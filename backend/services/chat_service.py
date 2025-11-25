import time
from typing import List, Optional, Dict, Any
from bson import ObjectId
from backend.services.db_service import get_db

class ChatService:
    def __init__(self):
        self.db = get_db()
        self.sessions = self.db["chat_sessions"]
        self.messages = self.db["chat_messages"]
        
        # Indexes - creating indexes can attempt to contact MongoDB during import
        # which breaks tests that don't run a Mongo instance. Guard these calls
        # so import-time database unavailability doesn't raise exceptions.
        try:
            self.sessions.create_index("user_id")
            self.sessions.create_index("updated_at")
            self.messages.create_index("session_id")
            self.messages.create_index("created_at")
        except Exception:
            # Couldn't create indexes (likely no Mongo available). Continue
            # without failing — the application can still operate in memory or
            # tests can mock DB interactions as needed.
            pass

    def create_session(self, user_id: str, title: str = "New Chat") -> str:
        doc = {
            "user_id": str(user_id),
            "title": title,
            "created_at": int(time.time()),
            "updated_at": int(time.time())
        }
        res = self.sessions.insert_one(doc)
        return str(res.inserted_id)

    def get_user_sessions(self, user_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        cursor = self.sessions.find({"user_id": str(user_id)}).sort("updated_at", -1).limit(limit)
        return [{
            "id": str(doc["_id"]),
            "title": doc.get("title", "Untitled"),
            "created_at": doc.get("created_at"),
            "updated_at": doc.get("updated_at")
        } for doc in cursor]

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        try:
            doc = self.sessions.find_one({"_id": ObjectId(session_id)})
            if doc:
                return {
                    "id": str(doc["_id"]),
                    "user_id": doc.get("user_id"),
                    "title": doc.get("title"),
                    "created_at": doc.get("created_at"),
                    "updated_at": doc.get("updated_at")
                }
        except Exception:
            pass
        return None

    def delete_session(self, session_id: str, user_id: str) -> bool:
        # Verify ownership
        try:
            res = self.sessions.delete_one({"_id": ObjectId(session_id), "user_id": str(user_id)})
            if res.deleted_count > 0:
                # Delete messages
                self.messages.delete_many({"session_id": session_id})
                return True
        except Exception:
            pass
        return False

    def add_message(self, session_id: str, role: str, content: str) -> Dict[str, Any]:
        now = int(time.time())
        doc = {
            "session_id": session_id,
            "role": role,
            "content": content,
            "created_at": now
        }
        self.messages.insert_one(doc)
        
        # Update session timestamp
        self.sessions.update_one(
            {"_id": ObjectId(session_id)},
            {"$set": {"updated_at": now}}
        )
        
        return {
            "role": role,
            "content": content,
            "created_at": now
        }

    def get_messages(self, session_id: str) -> List[Dict[str, Any]]:
        cursor = self.messages.find({"session_id": session_id}).sort("created_at", 1)
        return [{
            "role": doc["role"],
            "content": doc["content"],
            "created_at": doc.get("created_at")
        } for doc in cursor]

    def update_session_title(self, session_id: str, title: str, user_id: str) -> bool:
         try:
            res = self.sessions.update_one(
                {"_id": ObjectId(session_id), "user_id": str(user_id)},
                {"$set": {"title": title}}
            )
            return res.modified_count > 0
         except Exception:
             return False
