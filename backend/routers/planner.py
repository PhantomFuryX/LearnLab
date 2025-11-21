"""
API endpoints for Planner + Calendar (Phase 2)
"""

from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from fastapi.responses import FileResponse
from datetime import datetime, timedelta
from typing import List, Optional
import uuid
import json
import logging
import io

from backend.core.agents.planner_agent import PlannerAgent
from backend.core.models_planner import (
    CreatePlanRequest,
    PlanResponse,
    ModuleProgressRequest,
    ProgressResponse,
    ReminderRequest,
    ReminderResponse,
)
from backend.services.db_service import get_db
from backend.utils.auth import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/plans", tags=["Planner"])

# Initialize services
planner_agent = PlannerAgent()

class DBService:
    """Wrapper for MongoDB operations"""
    def __init__(self):
        self.db = get_db()
    
    def get_user_summaries(self, user_id: str, limit: int = 10) -> List[dict]:
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
        except Exception:
            return []
    
    def save_learning_plan(self, plan_id: str, plan: dict) -> bool:
        try:
            plan["_id"] = plan_id
            plan["created_at"] = datetime.utcnow()
            plan["updated_at"] = datetime.utcnow()
            self.db["learning_plans"].insert_one(plan)
            return True
        except Exception:
            return False
    
    def get_learning_plan(self, plan_id: str) -> Optional[dict]:
        try:
            return self.db["learning_plans"].find_one({"_id": plan_id})
        except Exception:
            return None
    
    def get_user_plans(self, user_id: str, status: Optional[str] = None, limit: int = 10) -> List[dict]:
        try:
            query = {"user_id": user_id}
            if status:
                query["status"] = status
            return list(
                self.db["learning_plans"]
                .find(query)
                .sort("created_at", -1)
                .limit(limit)
            )
        except Exception:
            return []
    
    def create_user_progress(self, user_id: str, plan_id: str) -> bool:
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
            return True
        except Exception:
            return False
    
    def get_user_progress(self, user_id: str, plan_id: str) -> Optional[dict]:
        try:
            return self.db["user_progress"].find_one(
                {"user_id": user_id, "plan_id": plan_id}
            )
        except Exception:
            return None
    
    def update_module_progress(self, user_id: str, plan_id: str, completed_module: dict) -> bool:
        try:
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
            if completed_module.get("quiz_score") is not None:
                progress = self.get_user_progress(user_id, plan_id)
                completed = progress.get("completed_modules", [])
                scores = [m.get("quiz_score") for m in completed if m.get("quiz_score") is not None]
                avg_score = sum(scores) / len(scores) if scores else None
                self.db["user_progress"].update_one(
                    {"user_id": user_id, "plan_id": plan_id},
                    {"$set": {"average_quiz_score": avg_score}},
                )
            return True
        except Exception:
            return False
    
    def create_schedule(self, user_id: str, plan_id: str, start_date: datetime, calendar_events: List[dict]) -> bool:
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
            return True
        except Exception:
            return False
    
    def save_ical_token(self, plan_id: str, token: str) -> bool:
        try:
            self.db["ical_tokens"].insert_one({
                "_id": plan_id,
                "token": token,
                "created_at": datetime.utcnow(),
            })
            return True
        except Exception:
            return False
    
    def verify_ical_token(self, plan_id: str, token: str) -> bool:
        try:
            doc = self.db["ical_tokens"].find_one({"_id": plan_id})
            return doc and doc.get("token") == token
        except Exception:
            return False
    
    def create_reminder(self, plan_id: str, reminder_config: dict) -> str:
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
            return reminder_id
        except Exception:
            return None

db_service = DBService()


# ============================================================================
# CREATE PLAN
# ============================================================================


@router.post("/", response_model=PlanResponse)
async def create_learning_plan(
    request: CreatePlanRequest,
    current_user: dict = Depends(get_current_user),
    background_tasks: BackgroundTasks = None,
):
    """
    Generate a personalized learning plan.

    Endpoint: POST /api/v1/plans
    """
    try:
        user_id = current_user["user_id"]
        logger.info(f"Creating learning plan for user {user_id}: {request.goal}")

        # Fetch past summaries if requested
        past_summaries = []
        if request.include_past_summaries:
            past_summaries = db_service.get_user_summaries(user_id, limit=10)

        # Generate plan using Planner Agent
        plan = planner_agent.generate_plan(
            goal=request.goal,
            skill_level=request.skill_level.value,
            hours_per_week=request.hours_per_week,
            duration_weeks=request.duration_weeks,
            topics=request.topics,
            past_summaries=past_summaries,
        )

        plan["user_id"] = user_id
        plan_id = str(uuid.uuid4())

        # Save plan to DB
        db_service.save_learning_plan(plan_id, plan)
        logger.info(f"✓ Saved learning plan: {plan_id}")

        # Create schedule and calendar events
        if background_tasks:
            background_tasks.add_task(
                _create_schedule_and_calendar,
                user_id,
                plan_id,
                plan,
            )

        # Create progress tracking document
        db_service.create_user_progress(user_id, plan_id)

        # Generate iCal export token
        ical_token = str(uuid.uuid4())
        db_service.save_ical_token(plan_id, ical_token)

        return PlanResponse(
            plan_id=plan_id,
            plan_title=plan.get("plan_title"),
            plan_overview=plan.get("plan_overview"),
            modules=plan.get("modules", []),
            milestones=plan.get("milestones", []),
            quiz_schedule=plan.get("quiz_schedule", []),
            total_hours_estimated=plan.get("total_hours_estimated"),
            ical_url=f"/api/v1/plans/{plan_id}/calendar.ics?token={ical_token}",
            created_at=datetime.utcnow(),
        )

    except Exception as e:
        logger.error(f"Error creating learning plan: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# GET PLAN
# ============================================================================


@router.get("/{plan_id}", response_model=dict)
async def get_plan(
    plan_id: str,
    current_user: dict = Depends(get_current_user),
):
    """
    Retrieve a learning plan with all details.

    Endpoint: GET /api/v1/plans/{plan_id}
    """
    try:
        plan = db_service.get_learning_plan(plan_id)
        if not plan:
            raise HTTPException(status_code=404, detail="Plan not found")

        # Check authorization
        if plan.get("user_id") != current_user["user_id"]:
            raise HTTPException(status_code=403, detail="Access denied")

        return plan

    except Exception as e:
        logger.error(f"Error fetching plan: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/")
async def list_user_plans(
    current_user: dict = Depends(get_current_user),
    status: Optional[str] = Query(None),
    limit: int = Query(10, ge=1, le=100),
):
    """
    List all learning plans for current user.

    Endpoint: GET /api/v1/plans?status=active&limit=10
    """
    try:
        plans = db_service.get_user_plans(
            current_user["user_id"],
            status=status,
            limit=limit,
        )
        return {"plans": plans, "count": len(plans)}

    except Exception as e:
        logger.error(f"Error listing plans: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# UPDATE PROGRESS
# ============================================================================


@router.patch("/{plan_id}/modules/{module_id}")
async def mark_module_complete(
    plan_id: str,
    module_id: str,
    request: ModuleProgressRequest,
    current_user: dict = Depends(get_current_user),
):
    """
    Mark a module as completed and update progress.

    Endpoint: PATCH /api/v1/plans/{plan_id}/modules/{module_id}
    """
    try:
        user_id = current_user["user_id"]

        # Verify user owns this plan
        plan = db_service.get_learning_plan(plan_id)
        if not plan or plan.get("user_id") != user_id:
            raise HTTPException(status_code=403, detail="Access denied")

        # Record completion
        completed_module = {
            "module_id": module_id,
            "completed_at": datetime.utcnow().isoformat(),
            "time_spent_hours": request.time_spent_hours,
            "quiz_score": request.quiz_score,
            "notes": request.notes,
        }

        db_service.update_module_progress(
            user_id,
            plan_id,
            completed_module,
        )

        # Update overall progress
        progress = db_service.get_user_progress(user_id, plan_id)
        completion_pct = (len(progress.get("completed_modules", [])) / len(plan.get("modules", []))) * 100

        logger.info(f"✓ Module {module_id} marked complete for user {user_id}")

        return ProgressResponse(
            plan_id=plan_id,
            completed_modules=progress.get("completed_modules", []),
            total_hours_spent=progress.get("total_hours_spent", 0),
            average_quiz_score=progress.get("average_quiz_score"),
            completion_percentage=completion_pct,
            streak_days=progress.get("streak_days", 0),
        )

    except Exception as e:
        logger.error(f"Error updating module progress: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# CALENDAR & REMINDERS
# ============================================================================


@router.get("/{plan_id}/calendar.ics")
async def export_calendar(
    plan_id: str,
    token: str = Query(...),
):
    """
    Export learning plan as iCalendar (.ics) file.

    Endpoint: GET /api/v1/plans/{plan_id}/calendar.ics?token={token}
    """
    try:
        # Verify token
        if not db_service.verify_ical_token(plan_id, token):
            raise HTTPException(status_code=403, detail="Invalid token")

        plan = db_service.get_learning_plan(plan_id)
        if not plan:
            raise HTTPException(status_code=404, detail="Plan not found")

        # Generate iCal content
        ical_content = _generate_ical(plan)

        return FileResponse(
            io.BytesIO(ical_content.encode()),
            media_type="text/calendar",
            filename=f"learning_plan_{plan_id}.ics",
        )

    except Exception as e:
        logger.error(f"Error exporting calendar: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{plan_id}/reminders", response_model=ReminderResponse)
async def create_reminder(
    plan_id: str,
    request: ReminderRequest,
    current_user: dict = Depends(get_current_user),
):
    """
    Create a reminder for a learning plan.

    Endpoint: POST /api/v1/plans/{plan_id}/reminders
    """
    try:
        user_id = current_user["user_id"]

        # Verify user owns this plan
        plan = db_service.get_learning_plan(plan_id)
        if not plan or plan.get("user_id") != user_id:
            raise HTTPException(status_code=403, detail="Access denied")

        reminder_id = db_service.create_reminder(plan_id, request.dict())

        logger.info(f"✓ Created reminder {reminder_id} for plan {plan_id}")

        return ReminderResponse(
            reminder_id=reminder_id,
            type=request.type,
            schedule=request.schedule,
            enabled=request.enabled,
            created_at=datetime.utcnow(),
        )

    except Exception as e:
        logger.error(f"Error creating reminder: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{plan_id}/progress", response_model=ProgressResponse)
async def get_progress(
    plan_id: str,
    current_user: dict = Depends(get_current_user),
):
    """
    Get user's progress in a learning plan.

    Endpoint: GET /api/v1/plans/{plan_id}/progress
    """
    try:
        user_id = current_user["user_id"]

        # Verify user owns this plan
        plan = db_service.get_learning_plan(plan_id)
        if not plan or plan.get("user_id") != user_id:
            raise HTTPException(status_code=403, detail="Access denied")

        progress = db_service.get_user_progress(user_id, plan_id)
        modules = plan.get("modules", [])
        completed_count = len(progress.get("completed_modules", []))
        completion_pct = (completed_count / len(modules) * 100) if modules else 0

        return ProgressResponse(
            plan_id=plan_id,
            completed_modules=progress.get("completed_modules", []),
            total_hours_spent=progress.get("total_hours_spent", 0),
            average_quiz_score=progress.get("average_quiz_score"),
            completion_percentage=completion_pct,
            streak_days=progress.get("streak_days", 0),
        )

    except Exception as e:
        logger.error(f"Error fetching progress: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================


def _create_schedule_and_calendar(user_id: str, plan_id: str, plan: dict):
    """
    Background task: Create schedule and calendar events from plan.
    """
    try:
        start_date = datetime.utcnow()
        calendar_events = []

        # Generate calendar events for each module
        for module in plan.get("modules", []):
            week = module.get("week", 1)
            event_start = start_date + timedelta(weeks=week - 1)
            event_end = event_start + timedelta(hours=module.get("estimated_hours", 5))

            calendar_events.append(
                {
                    "title": module.get("title"),
                    "description": module.get("description"),
                    "start": event_start.isoformat(),
                    "end": event_end.isoformat(),
                    "module_id": module.get("module_id"),
                }
            )

        # Save schedule to DB
        db_service.create_schedule(
            user_id,
            plan_id,
            start_date,
            calendar_events,
        )

        logger.info(f"✓ Created schedule with {len(calendar_events)} events for plan {plan_id}")

    except Exception as e:
        logger.error(f"Error creating schedule: {e}")


def _generate_ical(plan: dict) -> str:
    """
    Generate iCalendar (.ics) format from plan.
    """
    import io
    from icalendar import Calendar, Event
    from datetime import timedelta

    cal = Calendar()
    cal.add("prodid", "-//LearnLab//Learning Plans//EN")
    cal.add("version", "2.0")
    cal.add("calscale", "GREGORIAN")
    cal.add("method", "PUBLISH")
    cal.add("x-wr-calname", plan.get("plan_title", "Learning Plan"))
    cal.add("x-wr-timezone", "UTC")

    start_date = datetime.utcnow()

    # Add module events
    for module in plan.get("modules", []):
        event = Event()
        event.add("summary", module.get("title"))
        event.add("description", module.get("description", ""))

        week = module.get("week", 1)
        event_start = start_date + timedelta(weeks=week - 1)
        event_end = event_start + timedelta(hours=module.get("estimated_hours", 5))

        event.add("dtstart", event_start)
        event.add("dtend", event_end)
        event.add("uid", f"{module.get('module_id')}@learnlab.io")
        event.add("created", datetime.utcnow())
        event.add("last-modified", datetime.utcnow())

        cal.add_component(event)

    # Add milestone events
    for milestone in plan.get("milestones", []):
        event = Event()
        event.add("summary", f"[Milestone] {milestone.get('title')}")
        event.add("description", milestone.get("description", ""))

        week = milestone.get("week", 1)
        event_date = start_date + timedelta(weeks=week - 1)
        event.add("dtstart", event_date.date())
        event.add("uid", f"{milestone.get('title')}@learnlab.io")
        event.add("categories", ["MILESTONE"])

        cal.add_component(event)

    return cal.to_ical().decode("utf-8")
