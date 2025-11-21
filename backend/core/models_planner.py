"""
MongoDB models for Planner + Calendar Phase 2
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum


class SkillLevel(str, Enum):
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"


class DifficultyLevel(str, Enum):
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"


class ModuleStatus(str, Enum):
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    SKIPPED = "skipped"


class PlanStatus(str, Enum):
    ACTIVE = "active"
    COMPLETED = "completed"
    ARCHIVED = "archived"
    PAUSED = "paused"


class ReminderType(str, Enum):
    EMAIL = "email"
    PUSH = "push"
    SMS = "sms"


class MilestoneType(str, Enum):
    QUIZ = "quiz"
    PROJECT = "project"
    ASSESSMENT = "assessment"
    CHECKPOINT = "checkpoint"


# ============================================================================
# Learning Plan Models
# ============================================================================


class LearningOutcome(BaseModel):
    outcome: str
    description: Optional[str] = None


class ResourceRef(BaseModel):
    type: str  # "paper", "tutorial", "code", "video", "article"
    title: str
    url: Optional[str] = None
    summary_id: Optional[str] = None  # Link to existing summary doc


class Module(BaseModel):
    week: int
    module_id: str  # e.g., "mod_001"
    title: str
    description: str
    learning_outcomes: List[str]
    estimated_hours: float
    difficulty: DifficultyLevel
    resource_types: List[str]  # ["paper", "tutorial", "code_project"]
    key_topics: List[str]
    prerequisites: List[str]  # ["none"] or ["mod_001"]
    assigned_resources: List[ResourceRef] = Field(default_factory=list)
    status: ModuleStatus = ModuleStatus.NOT_STARTED


class Milestone(BaseModel):
    week: int
    milestone_id: str = Field(default_factory=lambda: f"milestone_{datetime.utcnow().timestamp()}")
    type: MilestoneType
    title: str
    description: str
    deliverables: List[str]
    due_date: Optional[datetime] = None
    is_completed: bool = False
    completion_date: Optional[datetime] = None


class QuizSchedule(BaseModel):
    week: int
    quiz_id: str = Field(default_factory=lambda: f"quiz_{datetime.utcnow().timestamp()}")
    module_ids: List[str]
    num_questions: int
    difficulty: DifficultyLevel
    topics: List[str]
    scheduled_date: Optional[datetime] = None


class LearningPlan(BaseModel):
    """Main learning plan document"""

    user_id: str
    plan_title: str
    plan_overview: str
    goal: str
    topic: str
    skill_level: SkillLevel
    hours_per_week: int
    duration_weeks: int
    total_hours_estimated: float
    difficulty_progression: str
    modules: List[Module]
    milestones: List[Milestone]
    quiz_schedule: List[QuizSchedule]
    success_criteria: List[str]
    notes: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    status: PlanStatus = PlanStatus.ACTIVE
    start_date: Optional[datetime] = None
    target_completion_date: Optional[datetime] = None

    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "user_123",
                "plan_title": "Master Agentic AI in 4 Weeks",
                "goal": "Understand agent architectures and build working examples",
                "skill_level": "intermediate",
                "hours_per_week": 5,
                "duration_weeks": 4,
            }
        }


# ============================================================================
# Schedule & Calendar Models
# ============================================================================


class Reminder(BaseModel):
    reminder_id: str = Field(default_factory=lambda: f"reminder_{datetime.utcnow().timestamp()}")
    type: ReminderType
    schedule: str  # "every_sunday_19:00" or "2025-11-25T19:00:00"
    enabled: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_sent: Optional[datetime] = None


class CalendarEvent(BaseModel):
    event_id: str = Field(default_factory=lambda: f"evt_{datetime.utcnow().timestamp()}")
    title: str
    description: Optional[str] = None
    start: datetime
    end: datetime
    module_id: Optional[str] = None
    milestone_id: Optional[str] = None
    location: Optional[str] = None
    is_synced: bool = False  # Has been added to external calendar


class Schedule(BaseModel):
    """Calendar and reminder schedule for a learning plan"""

    user_id: str
    plan_id: str  # Reference to LearningPlan._id
    start_date: datetime
    reminders: List[Reminder] = Field(default_factory=list)
    calendar_events: List[CalendarEvent] = Field(default_factory=list)
    ical_export_token: Optional[str] = None  # For public iCal URL
    timezone: str = "UTC"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "user_123",
                "plan_id": "plan_123",
                "start_date": "2025-11-24T00:00:00Z",
                "timezone": "America/New_York",
            }
        }


# ============================================================================
# Progress Tracking Models
# ============================================================================


class CompletedModule(BaseModel):
    module_id: str
    completed_at: datetime
    time_spent_hours: float = 0.0
    quiz_score: Optional[float] = None  # 0-100
    notes: Optional[str] = None


class UserProgress(BaseModel):
    """Track user progress through a learning plan"""

    user_id: str
    plan_id: str  # Reference to LearningPlan._id
    completed_modules: List[CompletedModule] = Field(default_factory=list)
    completed_milestones: List[str] = Field(default_factory=list)  # milestone_ids
    total_hours_spent: float = 0.0
    average_quiz_score: Optional[float] = None
    last_access: datetime = Field(default_factory=datetime.utcnow)
    streak_days: int = 0
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "user_123",
                "plan_id": "plan_123",
                "completed_modules": [],
                "total_hours_spent": 0.0,
            }
        }


# ============================================================================
# Request/Response Models
# ============================================================================


class CreatePlanRequest(BaseModel):
    """API request to generate a learning plan"""

    goal: str = Field(..., description="Learning goal (e.g., 'Master agentic AI')")
    skill_level: SkillLevel = Field(default=SkillLevel.INTERMEDIATE)
    hours_per_week: int = Field(default=5, ge=1, le=40)
    duration_weeks: int = Field(default=4, ge=1, le=52)
    topics: List[str] = Field(..., min_items=1, description="Topics to cover")
    include_past_summaries: bool = Field(default=True)

    class Config:
        json_schema_extra = {
            "example": {
                "goal": "Master agentic AI in 4 weeks",
                "skill_level": "intermediate",
                "hours_per_week": 5,
                "duration_weeks": 4,
                "topics": ["agent architectures", "tool use", "agentic loops"],
            }
        }


class PlanResponse(BaseModel):
    """API response with generated plan"""

    plan_id: str
    plan_title: str
    plan_overview: str
    modules: List[Module]
    milestones: List[Milestone]
    quiz_schedule: List[QuizSchedule]
    total_hours_estimated: float
    ical_url: str  # URL to download .ics file
    created_at: datetime


class ModuleProgressRequest(BaseModel):
    """Mark a module as complete"""

    status: ModuleStatus
    time_spent_hours: float
    quiz_score: Optional[float] = None
    notes: Optional[str] = None


class ProgressResponse(BaseModel):
    """User's progress in a plan"""

    plan_id: str
    completed_modules: List[CompletedModule]
    total_hours_spent: float
    average_quiz_score: Optional[float]
    completion_percentage: float
    streak_days: int


class ReminderRequest(BaseModel):
    """Set up a reminder"""

    type: ReminderType
    schedule: str = Field(..., description="Cron/iCal format or ISO datetime")
    enabled: bool = True


class ReminderResponse(BaseModel):
    """Confirmation of reminder creation"""

    reminder_id: str
    type: ReminderType
    schedule: str
    enabled: bool
    created_at: datetime
