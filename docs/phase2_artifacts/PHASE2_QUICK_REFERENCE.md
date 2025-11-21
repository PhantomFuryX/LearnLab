# Phase 2 Quick Reference Card

## 🎯 One-Page Cheatsheet

### Setup (Do This First)
```bash
# 1. Create indexes
python backend/scripts/setup_indexes.py

# 2. Start API
cd backend && python -m uvicorn main:app --reload
```

### API Endpoints

```
CREATE PLAN
POST /api/v1/plans
{
  "goal": "Learn X in Y weeks",
  "skill_level": "beginner|intermediate|advanced",
  "hours_per_week": 5-40,
  "duration_weeks": 1-52,
  "topics": ["topic1", "topic2"]
}
Response: {plan_id, plan_title, modules[], milestones[], ical_url}

LIST PLANS
GET /api/v1/plans?status=active&limit=10
Response: {plans[], count}

GET PLAN
GET /api/v1/plans/{plan_id}
Response: {full plan with modules, milestones, quizzes}

MARK COMPLETE
PATCH /api/v1/plans/{plan_id}/modules/{module_id}
{
  "status": "completed",
  "time_spent_hours": 5.5,
  "quiz_score": 85.0,
  "notes": "optional"
}
Response: {plan_id, completed_modules[], completion_percentage}

GET PROGRESS
GET /api/v1/plans/{plan_id}/progress
Response: {completed_modules[], total_hours_spent, average_quiz_score, completion_percentage, streak_days}

EXPORT CALENDAR
GET /api/v1/plans/{plan_id}/calendar.ics?token={token}
Response: .ics file (import to Google Calendar, Outlook, Apple Calendar)

CREATE REMINDER
POST /api/v1/plans/{plan_id}/reminders
{
  "type": "email|push|sms",
  "schedule": "every_sunday_19:00",
  "enabled": true
}
Response: {reminder_id, type, schedule, created_at}
```

### Quick Test
```bash
# 1. Get token (replace with your JWT)
TOKEN="your_jwt_token_here"

# 2. Create plan
PLAN=$(curl -X POST http://localhost:8000/api/v1/plans \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "goal": "Master agentic AI in 4 weeks",
    "skill_level": "intermediate",
    "hours_per_week": 5,
    "duration_weeks": 4,
    "topics": ["agent architectures", "tool use"]
  }')

PLAN_ID=$(echo $PLAN | jq -r '.plan_id')
ICAL_URL=$(echo $PLAN | jq -r '.ical_url')

# 3. Get plan
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/v1/plans/$PLAN_ID | jq

# 4. Download calendar
curl "$ICAL_URL" -o plan.ics

# 5. Mark module complete
curl -X PATCH http://localhost:8000/api/v1/plans/$PLAN_ID/modules/mod_001 \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "status": "completed",
    "time_spent_hours": 5,
    "quiz_score": 90
  }'
```

### Database Collections

```
learning_plans
├── _id: plan_id
├── user_id: user
├── plan_title: str
├── modules: [{week, module_id, title, ...}]
├── milestones: [{week, type, title, ...}]
├── quiz_schedule: [{week, num_questions, ...}]
└── created_at: datetime

user_progress
├── _id: "{user_id}_{plan_id}"
├── user_id: user
├── plan_id: plan
├── completed_modules: [{module_id, completed_at, time_spent_hours, quiz_score}]
├── total_hours_spent: float
├── average_quiz_score: float
└── streak_days: int

schedules
├── _id: "{user_id}_{plan_id}"
├── user_id: user
├── plan_id: plan
├── calendar_events: [{title, start, end, module_id}]
└── reminders: [{type, schedule, enabled}]

reminders
├── _id: reminder_id
├── plan_id: plan
├── type: "email|push|sms"
├── schedule: cron_pattern
├── enabled: bool
└── last_sent: datetime

ical_tokens
├── _id: plan_id
├── token: uuid
└── created_at: datetime (TTL: 90 days)
```

### Models/Schemas

```python
# CreatePlanRequest
goal: str
skill_level: "beginner" | "intermediate" | "advanced"
hours_per_week: 1-40
duration_weeks: 1-52
topics: [str]
include_past_summaries: bool

# Module
week: int
module_id: str
title: str
estimated_hours: float
difficulty: str
resource_types: [str]
key_topics: [str]

# Milestone
week: int
type: "quiz" | "project" | "assessment" | "checkpoint"
title: str
deliverables: [str]

# QuizSchedule
week: int
num_questions: 10
difficulty: str
topics: [str]
```

### Code Snippets

```python
# Generate a plan (Python)
from backend.core.agents.planner_agent import PlannerAgent

planner = PlannerAgent()
plan = planner.generate_plan(
    goal="Master RAG systems",
    skill_level="advanced",
    hours_per_week=10,
    duration_weeks=6,
    topics=["retrieval", "LLMs", "embeddings"],
)

# List plans (FastAPI route)
@router.get("/api/v1/plans")
async def list_plans(current_user = Depends(get_current_user)):
    plans = db["learning_plans"].find({"user_id": current_user["user_id"]})
    return {"plans": list(plans)}
```

### Common Errors

| Error | Solution |
|-------|----------|
| 401 Unauthorized | Check JWT token, ensure Authorization: Bearer {token} |
| 403 Access Denied | Ensure user owns the plan |
| 404 Not Found | Check plan_id exists |
| 500 LLM Error | Check OPENAI_API_KEY, rate limits |
| 500 DB Error | Check MongoDB connection, indexes created |

### Files You Need to Know

| File | Purpose |
|------|---------|
| `backend/routers/planner.py` | All 7 endpoints + DB operations |
| `backend/core/agents/planner_agent.py` | Plan generation logic |
| `backend/core/models_planner.py` | Pydantic schemas |
| `backend/scripts/setup_indexes.py` | Index creation |
| `backend/utils/auth.py` | get_current_user() |
| `backend/main.py` | Router registration |

### Next Steps

1. **Test**: Run `pytest tests/test_planner_integration.py -v`
2. **Frontend**: Build React components (Phase 2b)
3. **Reminders**: Set up Celery + Redis (optional)
4. **Deploy**: Docker + cloud (when ready)

### Docs

- **Full Design**: `docs/PHASE2_PLANNER_CALENDAR.md`
- **Integration**: `docs/PHASE2_INTEGRATION_GUIDE.md`
- **Summary**: `PHASE2_FINAL_SUMMARY.md`

---

**Last Updated**: November 21, 2025
**Status**: Production Ready ✅
