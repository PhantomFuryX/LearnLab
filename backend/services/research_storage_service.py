"""
Research Storage Service - stores research results in MongoDB
"""
from typing import List, Dict, Any, Optional
from datetime import datetime
from backend.services.db_service import get_db
from backend.utils.env_setup import get_logger
import uuid

logger = get_logger()

class ResearchStorageService:
    """Service to store and retrieve research results."""
    
    def __init__(self):
        self.logger = logger
        self.db = get_db()
        self.collection = self.db["research_results"]
    
    def store_research(
        self,
        query: str,
        namespace: str,
        results: List[Dict[str, Any]],
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Store research results in MongoDB.
        
        Returns:
            research_id: UUID of stored research
        """
        research_id = str(uuid.uuid4())
        
        document = {
            "_id": research_id,
            "query": query,
            "namespace": namespace,
            "results": results,
            "metadata": metadata or {},
            "created_at": datetime.utcnow(),
            "result_count": len(results)
        }
        
        try:
            self.collection.insert_one(document)
            self.logger.info(f"Stored research {research_id}: '{query}' with {len(results)} results")
            return research_id
        except Exception as e:
            self.logger.error(f"Failed to store research: {e}")
            raise
    
    def get_research(self, research_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve research by ID."""
        try:
            return self.collection.find_one({"_id": research_id})
        except Exception as e:
            self.logger.error(f"Failed to retrieve research {research_id}: {e}")
            return None
    
    def list_research(
        self,
        namespace: Optional[str] = None,
        limit: int = 50,
        skip: int = 0
    ) -> List[Dict[str, Any]]:
        """
        List recent research queries.
        
        Args:
            namespace: Filter by namespace (optional)
            limit: Max results
            skip: Skip N results (pagination)
            
        Returns:
            List of research documents (without full results)
        """
        query = {}
        if namespace:
            query["namespace"] = namespace
        
        try:
            cursor = self.collection.find(
                query,
                {"results": 0}  # Exclude full results for listing
            ).sort("created_at", -1).skip(skip).limit(limit)
            
            return list(cursor)
        except Exception as e:
            self.logger.error(f"Failed to list research: {e}")
            return []
    
    def search_research(
        self,
        query_text: str,
        namespace: Optional[str] = None,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Search stored research by query text.
        """
        search_filter = {
            "query": {"$regex": query_text, "$options": "i"}
        }
        if namespace:
            search_filter["namespace"] = namespace
        
        try:
            cursor = self.collection.find(search_filter).sort("created_at", -1).limit(limit)
            return list(cursor)
        except Exception as e:
            self.logger.error(f"Failed to search research: {e}")
            return []
    
    def delete_research(self, research_id: str) -> bool:
        """Delete research by ID."""
        try:
            result = self.collection.delete_one({"_id": research_id})
            return result.deleted_count > 0
        except Exception as e:
            self.logger.error(f"Failed to delete research {research_id}: {e}")
            return False

    def get_feed(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get a flattened feed of articles from recent research."""
        pipeline = [
            {"$sort": {"created_at": -1}},
            {"$limit": 20},  # Look at last 20 sessions
            {"$unwind": "$results"},
            # Sort by date if available, otherwise created_at
            {"$sort": {"results.date": -1}}, 
            {"$limit": limit},
            {"$project": {
                "title": "$results.title",
                "link": "$results.link",
                "excerpt": "$results.excerpt",
                "source": "$results.source",
                "date": "$results.date",
                "feed_title": "$results.feed_title",
                "query": "$query",
                "research_id": "$_id"
            }}
        ]
        try:
            return list(self.collection.aggregate(pipeline))
        except Exception as e:
            self.logger.error(f"Failed to get feed: {e}")
            return []
