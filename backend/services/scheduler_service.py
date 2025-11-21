import os
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from backend.utils.env_setup import get_logger
from backend.core.agents.research_agent import ResearchAgent

logger = get_logger("Scheduler")

class SchedulerService:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(SchedulerService, cls).__new__(cls)
            cls._instance.scheduler = AsyncIOScheduler()
            cls._instance.agent = ResearchAgent()
            cls._instance.initialized = False
        return cls._instance

    def __init__(self):
        if self.initialized:
            return
        self.initialized = True
        
    def start(self):
        """Start the scheduler."""
        if os.getenv("ENABLE_SCHEDULER", "1") == "1":
            self.scheduler.start()
            self._schedule_default_jobs()
            logger.info("Scheduler started.")
        else:
            logger.info("Scheduler disabled via env.")

    def _schedule_default_jobs(self):
        """Schedule default recurring jobs."""
        # Example: Daily AI News at 8am UTC
        self.scheduler.add_job(
            self.run_daily_research,
            CronTrigger(hour=8, minute=0),
            id="daily_ai_news",
            replace_existing=True
        )
        # Example: Hourly RSS check (if feeds configured)
        if os.getenv("RSS_FEEDS"):
            self.scheduler.add_job(
                self.run_rss_ingest,
                CronTrigger(minute=30), # Every hour at :30
                id="hourly_rss",
                replace_existing=True
            )
            
    async def run_daily_research(self):
        logger.info("Running daily AI research job...")
        try:
            await self.agent.search_and_store(
                query="latest AI agents research",
                namespace="daily-news",
                sources=["arxiv", "web"],
                max_results=20
            )
            logger.info("Daily research job completed.")
        except Exception as e:
            logger.error(f"Daily research job failed: {e}")

    async def run_rss_ingest(self):
        logger.info("Running RSS ingestion job...")
        try:
            # This will trigger the RSS logic in search()
            # We pass a dummy query that implies "all" from configured feeds
            # The ResearchAgent.search logic I wrote checks for RSS_FEEDS env var
            await self.agent.search_and_store(
                query="http://dummy", # Trigger RSS logic if URL, or we can rely on env vars
                namespace="rss-feed",
                sources=["rss"],
                max_results=10
            )
            # Actually, my ResearchAgent logic for RSS iterates feeds if query is not a URL.
            # Let's pass a generic query to filter, or empty.
            await self.agent.search_and_store(
                query="AI", # Filter for AI content in feeds
                namespace="rss-feed",
                sources=["rss"],
                max_results=10
            )
            logger.info("RSS ingestion job completed.")
        except Exception as e:
            logger.error(f"RSS ingestion job failed: {e}")
