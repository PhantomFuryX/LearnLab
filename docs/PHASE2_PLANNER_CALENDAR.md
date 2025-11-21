# Phase 2: Planner + Calendar Implementation

## Overview
Structured learning paths with auto-generated schedules, calendar integration, and reminder system.

---

## 1. Database Schema (MongoDB)

### Collections

#### `learning_plans`
```json
{
  "_id": ObjectId,
  "user_id": "user123",
  "goal": "Master agentic AI in 4 weeks",
  "topic": "agentic AI",
  "skill_level": "intermediate",  // beginner, intermediate, advanced
  "duration_weeks": 4,
  "hours_per_week": 5,
  "created_at": ISODate,
  "status": "active",  // active, completed, archived
  "modules": [
    {
      "week": 1,
      "module_id": "mod_001",
      "title": "Foundations of Agent Architecture",
      "summary_id": "summary_123",  // link to summary doc
      "resources": [
        {
          "type": "paper",
          "title": "Intro to Agent Loops",
          "url": "..."
        }
      ],
      "learning_outcomes": [
        "Understand agent decision loops",
        "Know tool-use patterns"
      ],
      "estimated_hours": 5,
      "difficulty": "beginner"
    }
  ],
  "milestones": [
    {
      "week": 2,
      "description": "Complete first code project",
      "due_date": ISODate,
      "is_completed": false
    }
  ]
}
```

#### `schedules`
```json
{
  "_id": ObjectId,
  "user_id": "user123",
  "plan_id": ObjectId,
  "start_date": ISODate,
  "reminders": [
    {
      "type": "email",  // email, push, sms
      "schedule": "every_sunday_19:00",
      "enabled": true
    }
  ],
  "calendar_events": [
    {
      "event_id": "evt_001",
      "title": "Study: Agent Architecture",
      "start": ISODate,
      "end": ISODate,
      "module_id": "mod_001",
      "description": "Read paper + watch tutorial"
    }
  ],
  "ical_export": "https://ical-export/uuid.ics"
}
```

#### `user_progress`
```json
{
  "_id": ObjectId,
  "user_id": "user123",
  "plan_id": ObjectId,
  "completed_modules": [
    {
      "module_id": "mod_001",
      "completed_at": ISODate,
      "quiz_score": 85,  // optional
      "notes": "..."
    }
  ],
  "total_hours_spent": 12.5,
  "last_access": ISODate,
  "streak_days": 7
}
```

---

## 2. Planner Agent (LangGraph)

### Input Schema
```python
class PlannerInput:
    user_goal: str  # "Master agentic AI in 4 weeks"
    available_hours_per_week: int  # 5
    skill_level: str  # "beginner", "intermediate", "advanced"
    duration_weeks: int  # 4
    topics: List[str]  # ["agent architectures", "tools"]
    past_summaries: List[SummaryMetadata]  # Existing learned content
```

### Output Schema
```python
class LearningPlan:
    title: str
    overview: str
    modules: List[Module]  # Week-by-week breakdown
    milestones: List[Milestone]
    total_hours: float
    difficulty_progression: str
    recommended_resources: List[Resource]
    quiz_schedule: List[QuizSchedule]
```

### Planner Logic (Pseudo-code)
1. **Analyze user goal** → extract domain + complexity
2. **Retrieve curriculum** → fetch existing summaries/modules matching topics
3. **Build schedule** → break into weekly chunks based on hours + skill
4. **Add milestones** → mark key checkpoints (week 2, week 4 = projects/quizzes)
5. **Generate quizzes** → schedule quiz after every 2 modules
6. **Output JSON** → formatted schedule ready for calendar creation

---

## 3. API Endpoints

### Create Learning Plan
```
POST /api/v1/plans
{
  "goal": "Master agentic AI in 4 weeks",
  "skill_level": "intermediate",
  "hours_per_week": 5,
  "duration_weeks": 4,
  "topics": ["agent architectures", "tool use"]
}
→ Returns: { plan_id, modules, milestones, ical_url }
```

### Get Plan Details
```
GET /api/v1/plans/{plan_id}
→ Returns: full learning plan with progress
```

### Mark Module Complete
```
PATCH /api/v1/plans/{plan_id}/modules/{module_id}
{
  "status": "completed",
  "quiz_score": 85,
  "time_spent_hours": 4.5
}
```

### Get Calendar Export
```
GET /api/v1/plans/{plan_id}/calendar.ics
→ Returns: iCalendar format (for Google Calendar, Outlook, etc.)
```

### Schedule Reminder
```
POST /api/v1/plans/{plan_id}/reminders
{
  "type": "email",
  "schedule": "every_sunday_19:00",
  "enabled": true
}
```

### Get User Progress
```
GET /api/v1/users/me/progress?plan_id={plan_id}
→ Returns: completed modules, quiz scores, streak, time spent
```

---

## 4. Reminder Queue Worker

Uses Celery to send scheduled reminders:

```python
@celery_app.task
def send_reminder(user_id, plan_id, reminder_type):
    # Fetch schedule config
    # Send email/push/SMS
    # Log in user_progress
    pass

@celery_app.on_after_finalize.connect
def setup_periodic_tasks(sender, **kwargs):
    # Check all active schedules every hour
    # Trigger reminders that are due
    sender.add_periodic_task(3600.0, check_and_send_reminders.s())
```

---

## 5. Implementation Steps

### Phase 2a: Backend (Week 1)
- [ ] Create MongoDB schema migrations
- [ ] Implement Planner Agent (LangGraph node)
- [ ] Build REST API endpoints
- [ ] Add reminder task to Celery

### Phase 2b: Frontend (Week 2)
- [ ] Plan creation form (goal, hours, skill level)
- [ ] Visual timeline/calendar view
- [ ] Progress dashboard
- [ ] Calendar export button

### Phase 2c: Integration (Week 3)
- [ ] Connect Planner to Research/Summarizer agents
- [ ] Auto-assign summaries to modules
- [ ] Quiz scheduling
- [ ] Email/push notifications

---

## 6. Sample Prompts

### Planner Agent System Prompt
```
You are an expert learning architect. Your role is to create personalized, 
structured learning plans based on user goals, available time, and skill level.

Given:
- User goal: {goal}
- Available: {hours_per_week} hours/week for {duration_weeks} weeks
- Skill level: {skill_level}
- Topics of interest: {topics}
- Past learning (summaries they've read): {summaries}

Create a week-by-week breakdown where:
1. Each module fits the available hours
2. Difficulty increases gradually
3. Milestones (quizzes, projects) occur every 2 weeks
4. Prerequisites are respected
5. Mix theory (papers) + practice (code) + quizzes

Output JSON with structure:
{
  "modules": [...],
  "milestones": [...],
  "difficulty_progression": "...",
  "notes": "..."
}
```

---

## Dependencies
- **MongoDB**: schema storage
- **Celery + Redis**: reminder scheduling
- **icalendar**: calendar export
- **LangGraph**: orchestration
- **FastAPI**: REST endpoints
- **APScheduler**: periodic task checks

---

## Success Metrics
✓ Users can generate plan in <2 seconds
✓ Calendar events sync with Google Calendar / Outlook
✓ Reminders sent 95% on time
✓ User completes 80%+ of scheduled modules
