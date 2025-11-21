"""
Summarizer Agent - creates structured summaries from research results
"""
from typing import List, Dict, Any, Optional
from datetime import datetime
from backend.services.llm_service import LLMService
from backend.utils.env_setup import get_logger
from pydantic import BaseModel

logger = get_logger()

class Summary(BaseModel):
    """Structured summary output"""
    headline: str
    tldr: str  # One-line summary
    key_points: List[str]  # 3-5 bullet points
    key_takeaways: List[str]  # Main insights
    claims: List[str]  # Key claims or findings
    methods: List[str]  # Methods or techniques mentioned
    applications: List[str]  # Potential applications

class SummarizerAgent:
    """
    Summarizer Agent creates structured summaries from research results.
    
    Inputs: Research results (papers, articles)
    Outputs: Structured summary with TL;DR, key points, claims, methods
    """
    
    def __init__(self):
        self.logger = logger
        self.llm = LLMService()
    
    async def summarize_single(
        self,
        title: str,
        content: str,
        source: str = "unknown"
    ) -> Summary:
        """
        Summarize a single research paper or article.
        
        Args:
            title: Paper/article title
            content: Full text or excerpt
            source: Source type (arxiv, web, etc.)
            
        Returns:
            Structured Summary object
        """
        prompt = self._build_summary_prompt(title, content, source)
        
        try:
            response = await self.llm.generate(
                prompt=prompt,
                temperature=0.3,  # Lower temp for more focused summaries
                max_tokens=1000
            )
            
            # Parse response into structured format
            summary_text = self._extract_text(response)
            summary = self._parse_summary_response(summary_text)
            
            self.logger.info(f"Summarized: '{title[:50]}...'")
            return summary
            
        except Exception as e:
            self.logger.error(f"Summarization failed: {e}")
            # Return basic summary on failure
            return Summary(
                headline=title,
                tldr="Summary generation failed",
                key_points=[],
                key_takeaways=[],
                claims=[],
                methods=[],
                applications=[]
            )
    
    async def summarize_multiple(
        self,
        results: List[Dict[str, Any]],
        aggregate: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Summarize multiple research results.
        
        Args:
            results: List of research results from ResearchAgent
            aggregate: If True, also create an aggregate summary
            
        Returns:
            List of summaries with metadata
        """
        summaries = []
        
        for result in results:
            title = result.get("title", "")
            excerpt = result.get("excerpt", "")
            source = result.get("source", "unknown")
            link = result.get("link", "")
            
            # Combine title and excerpt for summarization
            content = f"{title}\n\n{excerpt}"
            
            try:
                summary = await self.summarize_single(title, content, source)
                summaries.append({
                    "original": result,
                    "summary": summary.model_dump(),
                    "link": link,
                    "source": source
                })
            except Exception as e:
                self.logger.error(f"Failed to summarize '{title}': {e}")
                continue
        
        # Create aggregate summary if requested
        if aggregate and summaries:
            aggregate_summary = await self._create_aggregate_summary(summaries)
            return {
                "individual_summaries": summaries,
                "aggregate_summary": aggregate_summary,
                "total": len(summaries)
            }
        
        return summaries
    
    def _build_summary_prompt(self, title: str, content: str, source: str) -> str:
        """Build the summarization prompt."""
        return f"""You are an AI research summarizer. Create a structured summary of the following research content.

Title: {title}
Source: {source}
Content: {content}

Provide a structured summary in the following format:

HEADLINE: [A compelling one-line headline]

TL;DR: [One concise sentence summarizing the main point]

KEY POINTS:
- [Point 1]
- [Point 2]
- [Point 3]
- [Point 4]
- [Point 5]

KEY TAKEAWAYS:
- [Takeaway 1]
- [Takeaway 2]
- [Takeaway 3]

CLAIMS:
- [Key claim or finding 1]
- [Key claim or finding 2]

METHODS:
- [Method or technique 1]
- [Method or technique 2]

APPLICATIONS:
- [Potential application 1]
- [Potential application 2]

Focus on being concise, accurate, and extracting the most valuable insights."""

    def _extract_text(self, llm_response: Any) -> str:
        """Extract text from LLM response."""
        if isinstance(llm_response, dict):
            # OpenAI format
            if "choices" in llm_response:
                return llm_response["choices"][0].get("message", {}).get("content", "") or \
                       llm_response["choices"][0].get("text", "")
            # Anthropic format
            if "content" in llm_response:
                return llm_response["content"][0].get("text", "")
        return str(llm_response)
    
    def _parse_summary_response(self, text: str) -> Summary:
        """Parse LLM response into Summary object."""
        lines = text.strip().split('\n')
        
        headline = ""
        tldr = ""
        key_points = []
        key_takeaways = []
        claims = []
        methods = []
        applications = []
        
        current_section = None
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Detect sections
            if line.upper().startswith('HEADLINE:'):
                headline = line.split(':', 1)[1].strip()
            elif line.upper().startswith('TL;DR:'):
                tldr = line.split(':', 1)[1].strip()
            elif line.upper().startswith('KEY POINTS:'):
                current_section = 'key_points'
            elif line.upper().startswith('KEY TAKEAWAYS:'):
                current_section = 'key_takeaways'
            elif line.upper().startswith('CLAIMS:'):
                current_section = 'claims'
            elif line.upper().startswith('METHODS:'):
                current_section = 'methods'
            elif line.upper().startswith('APPLICATIONS:'):
                current_section = 'applications'
            elif line.startswith('-') or line.startswith('•'):
                # Bullet point
                item = line.lstrip('-•').strip()
                if current_section == 'key_points':
                    key_points.append(item)
                elif current_section == 'key_takeaways':
                    key_takeaways.append(item)
                elif current_section == 'claims':
                    claims.append(item)
                elif current_section == 'methods':
                    methods.append(item)
                elif current_section == 'applications':
                    applications.append(item)
        
        return Summary(
            headline=headline or "No headline",
            tldr=tldr or "No summary available",
            key_points=key_points[:5],  # Limit to 5
            key_takeaways=key_takeaways[:3],
            claims=claims[:3],
            methods=methods[:3],
            applications=applications[:3]
        )
    
    async def _create_aggregate_summary(self, summaries: List[Dict]) -> Dict[str, Any]:
        """Create an aggregate summary from multiple individual summaries."""
        # Combine all TLDRs and key points
        all_tldr = [s["summary"]["tldr"] for s in summaries]
        all_points = []
        for s in summaries:
            all_points.extend(s["summary"]["key_points"])
        
        combined_text = "\n".join(all_tldr[:10])  # Limit to prevent token overflow
        
        prompt = f"""Create a high-level summary that synthesizes the following research summaries:

{combined_text}

Provide:
1. An overall headline
2. A one-sentence synthesis
3. Top 5 common themes or insights

Format:
HEADLINE: [headline]
SYNTHESIS: [one sentence]
THEMES:
- [theme 1]
- [theme 2]
- [theme 3]
- [theme 4]
- [theme 5]
"""
        
        try:
            response = await self.llm.generate(prompt, temperature=0.3, max_tokens=300)
            text = self._extract_text(response)
            
            return {
                "aggregate_headline": text.split('\n')[0].replace('HEADLINE:', '').strip(),
                "synthesis": text,
                "source_count": len(summaries)
            }
        except Exception as e:
            self.logger.error(f"Aggregate summary failed: {e}")
            return {
                "aggregate_headline": "Research Summary",
                "synthesis": f"Summary of {len(summaries)} research items",
                "source_count": len(summaries)
            }
