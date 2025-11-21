"""
Chat Storage Service - stores chat sessions and messages in MongoDB
"""
from typing import List, Dict, Any, Optional
from datetime import datetime
from backend.services.db_service import get_db
from backend.utils.env_setup import get_logger
import uuid

logger = get_logger()

class ChatStorageService:
    def __init__(self):
        self.logger = logger
        self.db = get_db()
        self.sessions = self.db["chat_sessions"]
        self.sessions.create_index("user_id")
        self.sessions.create_index("updated_at")

    def create_session(self, user_id: str, title: str = "New Chat", mode: str = "chat") -> str:
        """Create a new chat session."""
        session_id = str(uuid.uuid4())
        doc = {
            "_id": session_id,
            "user_id": user_id,
            "title": title,
            "mode": mode,
            "messages": [],
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        self.sessions.insert_one(doc)
        return session_id

    def add_message(self, session_id: str, role: str, content: str):
        """Add a message to a session."""
        msg = {
            "role": role,
            "content": content,
            "timestamp": datetime.utcnow()
        }
        self.sessions.update_one(
            {"_id": session_id},
            {
                "$push": {"messages": msg},
                "$set": {"updated_at": datetime.utcnow()}
            }
        )

    def get_session(self, session_id: str, user_id: str) -> Optional[Dict[str, Any]]:
        """Get full session details."""
        return self.sessions.find_one({"_id": session_id, "user_id": user_id})

    def list_sessions(self, user_id: str, limit: int = 20) -> List[Dict[str, Any]]:
        """List user sessions (metadata only)."""
        cursor = self.sessions.find(
            {"user_id": user_id},
            {"messages": 0}  # Exclude messages for list view
        ).sort("updated_at", -1).limit(limit)
        return list(cursor)

    def update_title(self, session_id: str, title: str):
        self.sessions.update_one({"_id": session_id}, {"$set": {"title": title}})

    def delete_session(self, session_id: str, user_id: str):
        self.sessions.delete_one({"_id": session_id, "user_id": user_id})
