"""
Web Search Tool - searches the web for relevant articles
Uses DuckDuckGo (no API key needed) or Google Custom Search
"""
import httpx
from typing import List, Dict, Any
from datetime import datetime
import os
from backend.utils.env_setup import get_logger

logger = get_logger()

class WebSearchTool:
    """
    Tool to search the web for articles and content.
    Uses DuckDuckGo HTML search (no API key) as fallback.
    """
    
    def __init__(self):
        self.logger = logger
        self.google_api_key = os.getenv("GOOGLE_SEARCH_API_KEY")
        self.google_cx = os.getenv("GOOGLE_SEARCH_CX")
    
    async def search(
        self, 
        query: str, 
        max_results: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Search the web for relevant content.
        
        Args:
            query: Search query
            max_results: Maximum results
            
        Returns:
            List of result dictionaries with source="web"
        """
        # Try Google Custom Search if configured
        if self.google_api_key and self.google_cx:
            try:
                return await self._google_search(query, max_results)
            except Exception as e:
                self.logger.error(f"Google search failed: {e}")
        
        # Fallback to DuckDuckGo
        return await self._duckduckgo_search(query, max_results)
    
    async def _google_search(self, query: str, max_results: int) -> List[Dict[str, Any]]:
        """Search using Google Custom Search API."""
        url = "https://www.googleapis.com/customsearch/v1"
        params = {
            "key": self.google_api_key,
            "cx": self.google_cx,
            "q": query,
            "num": min(max_results, 10)  # Google max is 10 per request
        }
        
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            data = response.json()
        
        results = []
        for item in data.get("items", []):
            results.append({
                "source": "web",
                "title": item.get("title", ""),
                "link": item.get("link", ""),
                "excerpt": item.get("snippet", ""),
                "date": None,  # Google doesn't always provide dates
                "score": 0.7
            })
        
        self.logger.info(f"Google search for '{query}': {len(results)} results")
        return results
    
    async def _duckduckgo_search(self, query: str, max_results: int) -> List[Dict[str, Any]]:
        """
        Search using DuckDuckGo HTML (no API key required).
        Note: This is a simple scraper - for production, consider using their API or other services.
        """
        try:
            from bs4 import BeautifulSoup
        except ImportError:
            self.logger.error("BeautifulSoup not installed for web scraping")
            return []
        
        url = "https://html.duckduckgo.com/html/"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        data = {"q": query}
        
        try:
            async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
                response = await client.post(url, headers=headers, data=data)
                response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            results = []
            
            # Parse DuckDuckGo results
            for result in soup.find_all('div', class_='result'):
                if len(results) >= max_results:
                    break
                
                title_elem = result.find('a', class_='result__a')
                snippet_elem = result.find('a', class_='result__snippet')
                
                if title_elem:
                    title = title_elem.get_text(strip=True)
                    link = title_elem.get('href', '')
                    excerpt = snippet_elem.get_text(strip=True) if snippet_elem else ""
                    
                    results.append({
                        "source": "web",
                        "title": title,
                        "link": link,
                        "excerpt": excerpt,
                        "date": None,
                        "score": 0.6
                    })
            
            self.logger.info(f"DuckDuckGo search for '{query}': {len(results)} results")
            return results
            
        except Exception as e:
            self.logger.error(f"DuckDuckGo search failed: {e}")
            return []
