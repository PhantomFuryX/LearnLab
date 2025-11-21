"""
Memory Service - Manage user long-term memory and learning progress
"""
from typing import List, Dict, Any, Optional
from datetime import datetime
from backend.services.db_service import get_db
from backend.utils.env_setup import get_logger
import uuid

logger = get_logger()

class MemoryService:
    """Service to store and retrieve user memory (learning context)."""
    
    def __init__(self):
        self.logger = logger
        self.db = get_db()
        self.collection = self.db["user_memory"]
        self.collection.create_index([("user_id", 1), ("topic", 1)])
    
    def add_memory(self, user_id: str, topic: str, fact: str, context: str = ""):
        """Add a specific fact or memory about a topic."""
        doc = {
            "memory_id": str(uuid.uuid4()),
            "user_id": str(user_id),
            "topic": topic.lower().strip(),
            "fact": fact,
            "context": context,
            "created_at": datetime.utcnow(),
            "type": "fact"
        }
        try:
            self.collection.insert_one(doc)
        except Exception as e:
            self.logger.error(f"Failed to add memory: {e}")

    def log_struggle(self, user_id: str, topic: str, description: str):
        """Log that a user struggled with a concept."""
        doc = {
            "memory_id": str(uuid.uuid4()),
            "user_id": str(user_id),
            "topic": topic.lower().strip(),
            "fact": description,
            "created_at": datetime.utcnow(),
            "type": "struggle"
        }
        self.collection.insert_one(doc)

    def get_context(self, user_id: str, current_topic: str = "", limit: int = 5) -> str:
        """Get relevant context string for the LLM."""
        # Simple recent memory fetch
        # In a real system, this would use vector search over memories
        filter_q = {"user_id": str(user_id)}
        if current_topic:
            filter_q["topic"] = current_topic.lower().strip()
            
        cursor = self.collection.find(filter_q).sort("created_at", -1).limit(limit)
        memories = list(cursor)
        
        if not memories:
            return ""
            
        context_lines = ["User Memory/Context:"]
        for m in memories:
            kind = "Struggled with" if m.get("type") == "struggle" else "Learned"
            context_lines.append(f"- [{kind}] {m.get('fact')}")
            
        return "\n".join(context_lines)
