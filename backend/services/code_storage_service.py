"""
Code Storage Service - stores generated code examples in MongoDB
"""
from typing import List, Dict, Any, Optional
from datetime import datetime
from backend.services.db_service import get_db
from backend.utils.env_setup import get_logger
import uuid

logger = get_logger()

class CodeStorageService:
    """Service to store and retrieve generated code examples."""
    
    def __init__(self):
        self.logger = logger
        self.db = get_db()
        self.collection = self.db["code_examples"]
    
    def store_code(
        self,
        summary_id: str,
        query: str,
        code_examples: List[Dict[str, Any]],
        stack: str,
        language: str,
        namespace: str = "default",
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Store code examples in MongoDB.
        
        Args:
            summary_id: ID of the summary this code is based on
            query: Original query
            code_examples: List of code example objects
            stack: Target stack used
            language: Programming language
            namespace: Namespace
            metadata: Additional metadata
            
        Returns:
            code_collection_id: UUID of stored code collection
        """
        code_id = str(uuid.uuid4())
        
        document = {
            "_id": code_id,
            "summary_id": summary_id,
            "query": query,
            "namespace": namespace,
            "stack": stack,
            "language": language,
            "code_examples": code_examples,
            "metadata": metadata or {},
            "created_at": datetime.utcnow(),
            "example_count": len(code_examples)
        }
        
        try:
            self.collection.insert_one(document)
            self.logger.info(f"Stored code collection {code_id}: '{query}' with {len(code_examples)} examples")
            return code_id
        except Exception as e:
            self.logger.error(f"Failed to store code: {e}")
            raise
    
    def get_code(self, code_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve code collection by ID."""
        try:
            return self.collection.find_one({"_id": code_id})
        except Exception as e:
            self.logger.error(f"Failed to retrieve code {code_id}: {e}")
            return None
    
    def get_by_summary_id(self, summary_id: str) -> Optional[Dict[str, Any]]:
        """Get code associated with a summary ID."""
        try:
            return self.collection.find_one({"summary_id": summary_id})
        except Exception as e:
            self.logger.error(f"Failed to retrieve code for summary {summary_id}: {e}")
            return None
    
    def list_code(
        self,
        namespace: Optional[str] = None,
        stack: Optional[str] = None,
        language: Optional[str] = None,
        limit: int = 50,
        skip: int = 0
    ) -> List[Dict[str, Any]]:
        """
        List code examples with optional filters.
        
        Args:
            namespace: Filter by namespace
            stack: Filter by stack
            language: Filter by language
            limit: Max results
            skip: Skip N results
            
        Returns:
            List of code documents
        """
        query = {}
        if namespace:
            query["namespace"] = namespace
        if stack:
            query["stack"] = stack
        if language:
            query["language"] = language
        
        try:
            cursor = self.collection.find(
                query,
                {"code_examples.code": 0}  # Exclude full code for listing
            ).sort("created_at", -1).skip(skip).limit(limit)
            
            return list(cursor)
        except Exception as e:
            self.logger.error(f"Failed to list code: {e}")
            return []
    
    def delete_code(self, code_id: str) -> bool:
        """Delete code collection by ID."""
        try:
            result = self.collection.delete_one({"_id": code_id})
            return result.deleted_count > 0
        except Exception as e:
            self.logger.error(f"Failed to delete code {code_id}: {e}")
            return False
