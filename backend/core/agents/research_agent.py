"""
Research Agent - discovers AI knowledge from multiple sources
"""
import os
from typing import List, Dict, Any, Optional
from datetime import datetime
from backend.utils.env_setup import get_logger

logger = get_logger()

class ResearchAgent:
    """
    Research Agent discovers latest AI knowledge from multiple sources.
    
    Sources:
    - arXiv papers
    - Web search
    - RSS feeds (future)
    - Reddit/Twitter (future)
    """
    
    def __init__(self):
        self.logger = logger
        self.max_results = int(os.getenv("RESEARCH_MAX_RESULTS", "10"))
    
    
    async def search(
        self, 
        query: str, 
        sources: Optional[List[str]] = None,
        max_results: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Search for research papers and articles.
        
        Args:
            query: Search query (e.g., "agent architectures", "RAG systems")
            sources: List of sources to search ["arxiv", "web", "rss", "all"]
            max_results: Max results per source
            
        Returns:
            {
                "query": str,
                "timestamp": datetime,
                "results": [ ... ],
                "total": int
            }
        """
        if sources is None:
            sources = ["arxiv", "web"]
        
        if max_results is None:
            max_results = self.max_results
            
        all_results = []
        
        # Search RSS (if specific feeds are provided via env or config, or we treat query as URL)
        if "rss" in sources or "all" in sources:
            # If query looks like a URL, try to ingest as RSS
            if query.startswith("http"):
                rss_res = await self.ingest_rss(query, max_results)
                all_results.extend(rss_res)
            else:
                # Check for predefined feeds in env
                feeds = os.getenv("RSS_FEEDS", "").split(",")
                for feed in feeds:
                    if feed.strip():
                        rss_res = await self.ingest_rss(feed.strip(), max_results)
                        # Filter by query if needed, or just add all if broad topic
                        # Simple keyword filter
                        filtered = [r for r in rss_res if query.lower() in r['title'].lower() or query.lower() in r['excerpt'].lower()]
                        all_results.extend(filtered)

        # Search arXiv
        if "arxiv" in sources or "all" in sources:
            try:
                from backend.core.tools.arxiv_tool import ArxivTool
                arxiv_tool = ArxivTool()
                arxiv_results = await arxiv_tool.search(query, max_results=max_results)
                all_results.extend(arxiv_results)
                self.logger.info(f"Found {len(arxiv_results)} arXiv papers for '{query}'")
            except Exception as e:
                self.logger.error(f"arXiv search failed: {e}")
        
        # Search web
        if "web" in sources or "all" in sources:
            try:
                from backend.core.tools.web_search_tool import WebSearchTool
                web_tool = WebSearchTool()
                web_results = await web_tool.search(query, max_results=max_results)
                all_results.extend(web_results)
                self.logger.info(f"Found {len(web_results)} web results for '{query}'")
            except Exception as e:
                self.logger.error(f"Web search failed: {e}")
        
        # Rank and deduplicate
        ranked_results = self._rank_results(all_results)
        
        return {
            "query": query,
            "timestamp": datetime.utcnow(),
            "results": ranked_results,
            "total": len(ranked_results)
        }

    async def ingest_rss(self, url: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Ingest items from an RSS feed."""
        import feedparser
        import asyncio
        
        self.logger.info(f"Fetching RSS feed: {url}")
        
        def _fetch():
            return feedparser.parse(url)
            
        try:
            # feedparser is blocking, run in thread
            feed = await asyncio.to_thread(_fetch)
            results = []
            
            for entry in feed.entries[:limit]:
                # Extract useful fields
                title = entry.get("title", "No Title")
                link = entry.get("link", "")
                summary = entry.get("summary", "") or entry.get("description", "")
                published = entry.get("published_parsed") or entry.get("updated_parsed")
                
                date_obj = datetime.utcnow()
                if published:
                    try:
                        date_obj = datetime(*published[:6])
                    except:
                        pass
                
                # Simple HTML strip for summary
                import re
                clean_summary = re.sub('<[^<]+?>', '', summary)[:500] + "..."
                
                results.append({
                    "source": "rss",
                    "title": title,
                    "link": link,
                    "excerpt": clean_summary,
                    "date": date_obj,
                    "score": 0.8,  # Assume fresh feed items are relevant
                    "feed_title": feed.feed.get("title", "RSS Feed")
                })
                
            self.logger.info(f"Fetched {len(results)} items from RSS")
            return results
            
        except Exception as e:
            self.logger.error(f"RSS ingestion failed for {url}: {e}")
            return []

    
    def _rank_results(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Rank results by recency, relevance score, source priority.
        Remove duplicates by URL.
        """
        # Deduplicate by URL
        seen_urls = set()
        unique_results = []
        for r in results:
            url = r.get("link", "")
            if url and url not in seen_urls:
                seen_urls.add(url)
                unique_results.append(r)
        
        # Sort by score (desc), then date (desc)
        def sort_key(item):
            score = item.get("score", 0.5)
            date = item.get("date")
            # Convert date to timestamp for sorting (recent = higher)
            if date:
                if isinstance(date, datetime):
                    date_score = date.timestamp()
                else:
                    date_score = 0
            else:
                date_score = 0
            return (-score, -date_score)  # negative for descending
        
        unique_results.sort(key=sort_key)
        
        return unique_results
    
    async def search_and_store(
        self,
        query: str,
        namespace: str = "default",
        sources: Optional[List[str]] = None,
        max_results: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Search and store results in MongoDB for later retrieval.
        
        Returns the research results with storage confirmation.
        """
        from backend.services.research_storage_service import ResearchStorageService
        
        # Perform search
        results = await self.search(query, sources, max_results)
        
        # Store in MongoDB
        storage = ResearchStorageService()
        stored_id = storage.store_research(
            query=query,
            namespace=namespace,
            results=results["results"],
            metadata={
                "sources": sources or ["arxiv", "web"],
                "max_results": max_results or self.max_results
            }
        )
        
        results["stored_id"] = stored_id
        self.logger.info(f"Stored research results: {stored_id}")
        
        return results
