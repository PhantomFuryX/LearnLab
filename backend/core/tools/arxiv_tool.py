"""
arXiv API Tool - searches academic papers
"""
import httpx
from typing import List, Dict, Any
from datetime import datetime
import xml.etree.ElementTree as ET
from backend.utils.env_setup import get_logger

logger = get_logger()

class ArxivTool:
    """
    Tool to search arXiv for research papers.
    API docs: https://info.arxiv.org/help/api/index.html
    """
    
    BASE_URL = "https://export.arxiv.org/api/query"
    
    def __init__(self):
        self.logger = logger
    
    async def search(
        self, 
        query: str, 
        max_results: int = 10,
        sort_by: str = "submittedDate",  # submittedDate, lastUpdatedDate, relevance
        sort_order: str = "descending"
    ) -> List[Dict[str, Any]]:
        """
        Search arXiv papers.
        
        Args:
            query: Search query (e.g., "agent architectures", "ti:transformers")
            max_results: Maximum number of results
            sort_by: Sort field
            sort_order: ascending or descending
            
        Returns:
            List of paper dictionaries with source="arxiv"
        """
        params = {
            "search_query": f"all:{query}",
            "start": 0,
            "max_results": max_results,
            "sortBy": sort_by,
            "sortOrder": sort_order
        }
        
        try:
            async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
                response = await client.get(self.BASE_URL, params=params)
                response.raise_for_status()
                
            # Parse XML response
            results = self._parse_arxiv_xml(response.text)
            self.logger.info(f"arXiv search for '{query}': {len(results)} results")
            return results
            
        except Exception as e:
            self.logger.error(f"arXiv search failed for '{query}': {e}")
            return []
    
    def _parse_arxiv_xml(self, xml_text: str) -> List[Dict[str, Any]]:
        """Parse arXiv API XML response."""
        results = []
        
        try:
            root = ET.fromstring(xml_text)
            # arXiv uses Atom namespace
            ns = {'atom': 'http://www.w3.org/2005/Atom'}
            
            for entry in root.findall('atom:entry', ns):
                # Extract fields
                title = entry.find('atom:title', ns)
                title_text = title.text.strip().replace('\n', ' ') if title is not None else ""
                
                summary = entry.find('atom:summary', ns)
                summary_text = summary.text.strip().replace('\n', ' ')[:500] if summary is not None else ""
                
                link = entry.find('atom:id', ns)
                link_url = link.text.strip() if link is not None else ""
                
                published = entry.find('atom:published', ns)
                published_date = None
                if published is not None:
                    try:
                        published_date = datetime.fromisoformat(published.text.strip().replace('Z', '+00:00'))
                    except:
                        pass
                
                # Authors
                authors = []
                for author in entry.findall('atom:author', ns):
                    name = author.find('atom:name', ns)
                    if name is not None:
                        authors.append(name.text.strip())
                
                # Categories
                categories = []
                for category in entry.findall('atom:category', ns):
                    term = category.get('term')
                    if term:
                        categories.append(term)
                
                results.append({
                    "source": "arxiv",
                    "title": title_text,
                    "link": link_url,
                    "excerpt": summary_text,
                    "date": published_date,
                    "score": 0.8,  # Default score for arXiv (trusted source)
                    "authors": authors,
                    "categories": categories
                })
                
        except Exception as e:
            self.logger.error(f"Failed to parse arXiv XML: {e}")
        
        return results
