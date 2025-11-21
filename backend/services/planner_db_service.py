"""
MongoDB service for Planner + Calendar operations
Add these methods to your existing DBService class
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
import uuid
import logging

logger = logging.getLogger(__name__)


class PlannerDBService:
    """
    Mixin class for MongoDB operations related to Planner + Calendar.
    Integrate these methods into your existing DBService class.
    """

    # ========================================================================
    # LEARNING PLANS
    # ========================================================================

    def save_learning_plan(self, plan_id: str, plan: Dict[str, Any]) -> bool:
        """Save a learning plan to MongoDB"""
        try:
            plan["_id"] = plan_id
            plan["created_at"] = datetime.utcnow()
            plan["updated_at"] = datetime.utcnow()

            self.db["learning_plans"].insert_one(plan)
            logger.info(f"✓ Saved learning plan: {plan_id}")
            return True

        except Exception as e:
            logger.error(f"Error saving learning plan: {e}")
            return False

    def get_learning_plan(self, plan_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a learning plan"""
        try:
            return self.db["learning_plans"].find_one({"_id": plan_id})
        except Exception as e:
            logger.error(f"Error retrieving learning plan: {e}")
            return None

    def get_user_plans(
        self,
        user_id: str,
        status: Optional[str] = None,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """Get all plans for a user"""
        try:
            query = {"user_id": user_id}
            if status:
                query["status"] = status

            plans = list(
                self.db["learning_plans"]
                .find(query)
                .sort("created_at", -1)
                .limit(limit)
            )

            return plans

        except Exception as e:
            logger.error(f"Error retrieving user plans: {e}")
            return []

    def update_plan_status(self, plan_id: str, status: str) -> bool:
        """Update plan status"""
        try:
            self.db["learning_plans"].update_one(
                {"_id": plan_id},
                {
                    "$set": {
                        "status": status,
                        "updated_at": datetime.utcnow(),
                    }
                },
            )
            logger.info(f"✓ Updated plan {plan_id} status to {status}")
            return True

        except Exception as e:
            logger.error(f"Error updating plan status: {e}")
            return False

    # ========================================================================
    # USER PROGRESS
    # ========================================================================

    def create_user_progress(self, user_id: str, plan_id: str) -> bool:
        """Initialize progress tracking for a user-plan pair"""
        try:
            progress = {
                "_id": f"{user_id}_{plan_id}",
                "user_id": user_id,
                "plan_id": plan_id,
                "completed_modules": [],
                "completed_milestones": [],
                "total_hours_spent": 0.0,
                "average_quiz_score": None,
                "last_access": datetime.utcnow(),
                "streak_days": 0,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
            }

            self.db["user_progress"].insert_one(progress)
            logger.info(f"✓ Created progress tracking for {user_id}/{plan_id}")
            return True

        except Exception as e:
            logger.error(f"Error creating user progress: {e}")
            return False

    def get_user_progress(self, user_id: str, plan_id: str) -> Optional[Dict[str, Any]]:
        """Get user's progress in a specific plan"""
        try:
            return self.db["user_progress"].find_one(
                {"user_id": user_id, "plan_id": plan_id}
            )
        except Exception as e:
            logger.error(f"Error retrieving user progress: {e}")
            return None

    def update_module_progress(
        self,
        user_id: str,
        plan_id: str,
        completed_module: Dict[str, Any],
    ) -> bool:
        """Mark a module as completed"""
        try:
            # Add to completed modules
            self.db["user_progress"].update_one(
                {"user_id": user_id, "plan_id": plan_id},
                {
                    "$push": {"completed_modules": completed_module},
                    "$inc": {"total_hours_spent": completed_module.get("time_spent_hours", 0)},
                    "$set": {
                        "last_access": datetime.utcnow(),
                        "updated_at": datetime.utcnow(),
                    },
                },
            )

            # Update average quiz score if provided
            if completed_module.get("quiz_score") is not None:
                progress = self.get_user_progress(user_id, plan_id)
                completed = progress.get("completed_modules", [])
                scores = [m.get("quiz_score") for m in completed if m.get("quiz_score") is not None]
                avg_score = sum(scores) / len(scores) if scores else None

                self.db["user_progress"].update_one(
                    {"user_id": user_id, "plan_id": plan_id},
                    {"$set": {"average_quiz_score": avg_score}},
                )

            logger.info(f"✓ Updated progress for module {completed_module.get('module_id')}")
            return True

        except Exception as e:
            logger.error(f"Error updating module progress: {e}")
            return False

    def update_streak(self, user_id: str, plan_id: str, days: int) -> bool:
        """Update streak days for a user"""
        try:
            self.db["user_progress"].update_one(
                {"user_id": user_id, "plan_id": plan_id},
                {
                    "$set": {
                        "streak_days": days,
                        "updated_at": datetime.utcnow(),
                    }
                },
            )
            return True

        except Exception as e:
            logger.error(f"Error updating streak: {e}")
            return False

    # ========================================================================
    # SCHEDULES & CALENDAR
    # ========================================================================

    def create_schedule(
        self,
        user_id: str,
        plan_id: str,
        start_date: datetime,
        calendar_events: List[Dict[str, Any]],
    ) -> bool:
        """Create a schedule with calendar events"""
        try:
            schedule = {
                "_id": f"{user_id}_{plan_id}",
                "user_id": user_id,
                "plan_id": plan_id,
                "start_date": start_date,
                "reminders": [],
                "calendar_events": calendar_events,
                "timezone": "UTC",
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
            }

            self.db["schedules"].insert_one(schedule)
            logger.info(f"✓ Created schedule for {plan_id}")
            return True

        except Exception as e:
            logger.error(f"Error creating schedule: {e}")
            return False

    def get_schedule(self, user_id: str, plan_id: str) -> Optional[Dict[str, Any]]:
        """Get schedule for a user-plan pair"""
        try:
            return self.db["schedules"].find_one(
                {"user_id": user_id, "plan_id": plan_id}
            )
        except Exception as e:
            logger.error(f"Error retrieving schedule: {e}")
            return None

    # ========================================================================
    # REMINDERS
    # ========================================================================

    def create_reminder(self, plan_id: str, reminder_config: Dict[str, Any]) -> str:
        """Create a reminder for a plan"""
        try:
            reminder_id = str(uuid.uuid4())
            reminder = {
                "_id": reminder_id,
                "plan_id": plan_id,
                "type": reminder_config.get("type"),
                "schedule": reminder_config.get("schedule"),
                "enabled": reminder_config.get("enabled", True),
                "created_at": datetime.utcnow(),
                "last_sent": None,
            }

            self.db["reminders"].insert_one(reminder)
            logger.info(f"✓ Created reminder {reminder_id} for plan {plan_id}")
            return reminder_id

        except Exception as e:
            logger.error(f"Error creating reminder: {e}")
            return None

    def get_active_reminders(self) -> List[Dict[str, Any]]:
        """Get all active reminders that need to be processed"""
        try:
            return list(
                self.db["reminders"].find({"enabled": True})
            )
        except Exception as e:
            logger.error(f"Error retrieving reminders: {e}")
            return []

    def update_reminder_sent(self, reminder_id: str) -> bool:
        """Update last_sent timestamp for a reminder"""
        try:
            self.db["reminders"].update_one(
                {"_id": reminder_id},
                {"$set": {"last_sent": datetime.utcnow()}},
            )
            return True

        except Exception as e:
            logger.error(f"Error updating reminder: {e}")
            return False

    def disable_reminder(self, reminder_id: str) -> bool:
        """Disable a reminder"""
        try:
            self.db["reminders"].update_one(
                {"_id": reminder_id},
                {"$set": {"enabled": False}},
            )
            return True

        except Exception as e:
            logger.error(f"Error disabling reminder: {e}")
            return False

    # ========================================================================
    # ICAL TOKENS
    # ========================================================================

    def save_ical_token(self, plan_id: str, token: str) -> bool:
        """Save iCal export token"""
        try:
            self.db["ical_tokens"].insert_one({
                "_id": plan_id,
                "token": token,
                "created_at": datetime.utcnow(),
            })
            return True

        except Exception as e:
            logger.error(f"Error saving iCal token: {e}")
            return False

    def verify_ical_token(self, plan_id: str, token: str) -> bool:
        """Verify iCal token is valid"""
        try:
            doc = self.db["ical_tokens"].find_one({"_id": plan_id})
            return doc and doc.get("token") == token

        except Exception as e:
            logger.error(f"Error verifying iCal token: {e}")
            return False

    # ========================================================================
    # UTILITY METHODS
    # ========================================================================

    def get_user_summaries(self, user_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get user's past summaries (for context when generating plans).
        Assumes a 'summaries' collection exists.
        """
        try:
            summaries = list(
                self.db["summaries"]
                .find({"user_id": user_id})
                .sort("created_at", -1)
                .limit(limit)
            )

            return [
                {
                    "title": s.get("title"),
                    "headline": s.get("headline"),
                    "topics": s.get("topics", []),
                }
                for s in summaries
            ]

        except Exception as e:
            logger.warning(f"Could not retrieve summaries: {e}")
            return []

    def get_due_milestones(self, user_id: str, plan_id: str) -> List[Dict[str, Any]]:
        """Get upcoming milestones for a user"""
        try:
            plan = self.get_learning_plan(plan_id)
            if not plan:
                return []

            milestones = plan.get("milestones", [])
            today = datetime.utcnow().date()

            due = [
                m for m in milestones
                if m.get("due_date") and datetime.fromisoformat(m.get("due_date")).date() >= today
            ]

            return due

        except Exception as e:
            logger.error(f"Error getting due milestones: {e}")
            return []
