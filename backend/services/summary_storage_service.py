"""
Summary Storage Service - stores and retrieves summaries in MongoDB
"""
from typing import List, Dict, Any, Optional
from datetime import datetime
from backend.services.db_service import get_db
from backend.utils.env_setup import get_logger
import uuid

logger = get_logger()

class SummaryStorageService:
    """Service to store and retrieve research summaries."""
    
    def __init__(self):
        self.logger = logger
        self.db = get_db()
        self.collection = self.db["summaries"]
    
    def store_summary(
        self,
        research_id: str,
        query: str,
        summaries: List[Dict[str, Any]],
        aggregate_summary: Optional[Dict[str, Any]] = None,
        namespace: str = "default",
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Store summaries in MongoDB.
        
        Args:
            research_id: ID of the original research
            query: Original query
            summaries: List of individual summaries
            aggregate_summary: Optional aggregate summary
            namespace: Namespace
            metadata: Additional metadata
            
        Returns:
            summary_id: UUID of stored summary collection
        """
        summary_id = str(uuid.uuid4())
        
        document = {
            "_id": summary_id,
            "research_id": research_id,
            "query": query,
            "namespace": namespace,
            "summaries": summaries,
            "aggregate_summary": aggregate_summary,
            "metadata": metadata or {},
            "created_at": datetime.utcnow(),
            "summary_count": len(summaries)
        }
        
        try:
            self.collection.insert_one(document)
            self.logger.info(f"Stored summary {summary_id}: '{query}' with {len(summaries)} items")
            return summary_id
        except Exception as e:
            self.logger.error(f"Failed to store summary: {e}")
            raise
    
    def get_summary(self, summary_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve summary by ID."""
        try:
            return self.collection.find_one({"_id": summary_id})
        except Exception as e:
            self.logger.error(f"Failed to retrieve summary {summary_id}: {e}")
            return None
    
    def get_by_research_id(self, research_id: str) -> Optional[Dict[str, Any]]:
        """Get summary associated with a research ID."""
        try:
            return self.collection.find_one({"research_id": research_id})
        except Exception as e:
            self.logger.error(f"Failed to retrieve summary for research {research_id}: {e}")
            return None
    
    def list_summaries(
        self,
        namespace: Optional[str] = None,
        limit: int = 50,
        skip: int = 0
    ) -> List[Dict[str, Any]]:
        """
        List recent summaries.
        
        Args:
            namespace: Filter by namespace
            limit: Max results
            skip: Skip N results
            
        Returns:
            List of summary documents (without full summaries for performance)
        """
        query = {}
        if namespace:
            query["namespace"] = namespace
        
        try:
            cursor = self.collection.find(
                query,
                {"summaries": 0}  # Exclude full summaries for listing
            ).sort("created_at", -1).skip(skip).limit(limit)
            
            return list(cursor)
        except Exception as e:
            self.logger.error(f"Failed to list summaries: {e}")
            return []
    
    def search_summaries(
        self,
        query_text: str,
        namespace: Optional[str] = None,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """Search summaries by query text."""
        search_filter = {
            "query": {"$regex": query_text, "$options": "i"}
        }
        if namespace:
            search_filter["namespace"] = namespace
        
        try:
            cursor = self.collection.find(search_filter).sort("created_at", -1).limit(limit)
            return list(cursor)
        except Exception as e:
            self.logger.error(f"Failed to search summaries: {e}")
            return []
    
    def delete_summary(self, summary_id: str) -> bool:
        """Delete summary by ID."""
        try:
            result = self.collection.delete_one({"_id": summary_id})
            return result.deleted_count > 0
        except Exception as e:
            self.logger.error(f"Failed to delete summary {summary_id}: {e}")
            return False
