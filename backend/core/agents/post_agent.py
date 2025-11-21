"""
Post Agent - generates social media posts and triggers automation
"""
from typing import List, Dict, Any, Optional
from backend.services.llm_service import LLMService
from backend.utils.env_setup import get_logger
from backend.core.tools.n8n_tool import N8NTool
import json

from backend.services.db_service import get_db
import time
import uuid

logger = get_logger()

class PostAgent:
    """
    Post Agent creates social media content and publishes via N8N.
    """
    
    def __init__(self):
        self.logger = logger
        self.llm = LLMService()
        self.n8n = N8NTool()
        self.db = get_db()
        self.posts_col = self.db["posts"]
        
    async def generate_post(
        self,
        content: str,
        platform: str = "linkedin",  # linkedin, twitter
        tone: str = "professional"
    ) -> Dict[str, Any]:
        """Generate a post draft."""
        
        prompt = f"""You are an expert social media manager. Create a post for {platform}.
        
        Content Source:
        {content[:2000]}
        
        Tone: {tone}
        
        Requirements:
        - Platform: {platform}
        - Include relevant hashtags.
        - For Twitter: Create a thread (max 3 tweets).
        - For LinkedIn: Use structured formatting (bullet points).
        - Suggest an image prompt for DALL-E.
        
        Output JSON:
        {{
            "post_text": "string (or list of strings for twitter)",
            "image_prompt": "string",
            "hashtags": ["tag1", "tag2"]
        }}
        """
        
        try:
            response = await self.llm.generate(prompt, max_tokens=500)
            text = self._extract_text(response)
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0].strip()
            elif "```" in text:
                text = text.split("```")[1].split("```")[0].strip()
            
            data = json.loads(text)
            
            # Save draft
            post_id = str(uuid.uuid4())
            doc = {
                "post_id": post_id,
                "content": data,
                "source_content": content[:200], # Snippet
                "platform": platform,
                "tone": tone,
                "status": "draft",
                "created_at": int(time.time())
            }
            self.posts_col.insert_one(doc)
            data["post_id"] = post_id
            
            return data
        except Exception as e:
            self.logger.error(f"Post generation failed: {e}")
            return {"error": str(e)}

    async def publish_post(self, post_data: Dict[str, Any]) -> Dict[str, Any]:
        """Trigger N8N webhook to publish."""
        try:
            # Calls the 'social_post' workflow in N8N
            result = self.n8n.run("social_post", post_data)
            
            # Update status if post_id exists
            if "post_id" in post_data:
                self.posts_col.update_one(
                    {"post_id": post_data["post_id"]},
                    {"$set": {"status": "published", "published_at": int(time.time())}}
                )
            
            return result
        except Exception as e:
            self.logger.error(f"Publish failed: {e}")
            return {"error": str(e)}

    def _extract_text(self, llm_response: Any) -> str:
        if isinstance(llm_response, dict):
            if "choices" in llm_response:
                return llm_response["choices"][0].get("message", {}).get("content", "") or \
                       llm_response["choices"][0].get("text", "")
            if "content" in llm_response:
                return llm_response["content"][0].get("text", "")
        return str(llm_response)
