# Phase 2 Integration Guide: Planner + Calendar

This guide walks you through integrating the Planner Agent and Calendar system into your existing LearnLab backend.

---

## 1. File Structure

You've been provided with these new files:

```
backend/
├── core/
│   ├── agents/
│   │   └── planner_agent.py          [NEW] Planner Agent
│   └── models_planner.py              [NEW] MongoDB models
├── routers/
│   └── planner.py                     [NEW] API endpoints
├── services/
│   └── planner_db_service.py          [NEW] DB methods
├── tasks/
│   └── reminder_tasks.py              [NEW] Celery tasks
└── main.py                            [MODIFY] Add routes

docs/
├── PHASE2_PLANNER_CALENDAR.md         [NEW] Design doc
└── PHASE2_INTEGRATION_GUIDE.md        [THIS FILE]
```

---

## 2. Step-by-Step Integration

### Step 1: Update `backend/main.py`

Include the planner routes in your FastAPI app:

```python
# backend/main.py

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import planner  # ADD THIS

app = FastAPI(
    title="LearnLab API",
    description="AI-powered learning platform",
)

# ... existing middleware ...

# ADD THIS BLOCK:
app.include_router(planner.router)

# ... rest of your app ...
```

### Step 2: Merge `PlannerDBService` into your `DBService`

Your `services/db_service.py` should inherit or include all methods from `planner_db_service.py`:

```python
# backend/services/db_service.py

from services.planner_db_service import PlannerDBService

class DBService(PlannerDBService):
    """
    Main database service.
    Inherits planner methods from PlannerDBService.
    """
    
    def __init__(self, mongo_uri: str = None):
        # ... your existing init code ...
        pass

    # Your existing methods here
    # + All methods from PlannerDBService
```

Or copy-paste all `PlannerDBService` methods directly into `DBService`.

### Step 3: Update MongoDB Indexes

Create indexes for optimal performance:

```python
# backend/core/base.py or a migration file

def create_indexes(db):
    """Create indexes for Phase 2 collections"""
    
    # Learning Plans
    db["learning_plans"].create_index("user_id")
    db["learning_plans"].create_index([("user_id", 1), ("status", 1)])
    db["learning_plans"].create_index("created_at")
    
    # User Progress
    db["user_progress"].create_index([("user_id", 1), ("plan_id", 1)])
    db["user_progress"].create_index("plan_id")
    
    # Schedules
    db["schedules"].create_index([("user_id", 1), ("plan_id", 1)])
    
    # Reminders
    db["reminders"].create_index("plan_id")
    db["reminders"].create_index([("enabled", 1), ("schedule", 1)])
    
    # iCal Tokens
    db["ical_tokens"].create_index("created_at", expireAfterSeconds=7776000)  # 90 days
```

Call this on app startup or via migration script.

### Step 4: Update `requirements.txt`

Add the necessary Python packages:

```txt
icalendar==5.0.0
python-cron==0.7.1
celery>=5.3.0
redis>=4.5.0
```

Install: `pip install -r requirements.txt`

### Step 5: Configure Celery for Reminders

Update your Celery configuration:

```python
# backend/celery_app.py or where you define Celery

from celery import Celery
from celery.schedules import crontab

app = Celery("learnlab")

app.conf.update(
    broker_url="redis://localhost:6379/0",
    result_backend="redis://localhost:6379/0",
    timezone="UTC",
    enable_utc=True,
)

# Add Celery Beat schedule for periodic tasks
app.conf.beat_schedule = {
    'check-reminders-hourly': {
        'task': 'tasks.reminder_tasks.check_and_send_reminders',
        'schedule': crontab(minute=0),  # Every hour on the hour
    },
    'calculate-streaks-daily': {
        'task': 'tasks.reminder_tasks.calculate_user_streaks',
        'schedule': crontab(hour=0, minute=0),  # Daily at midnight UTC
    },
}

# Load tasks
app.autodiscover_tasks(['tasks'])
```

### Step 6: Update Authentication

Ensure your `utils/auth.py` has `get_current_user`:

```python
# backend/utils/auth.py

from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer

security = HTTPBearer()

async def get_current_user(credentials = Depends(security)):
    """Extract user from JWT or session"""
    # Your existing auth logic
    user_id = extract_user_id(credentials)  # Implement based on your auth
    return {"user_id": user_id, "email": "..."}  # Return user dict
```

### Step 7: Create Notification Service (Optional but Recommended)

For sending reminders via email/push/SMS:

```python
# backend/services/notification_service.py

class NotificationService:
    """Handle user notifications"""
    
    def send_email(self, to: str, subject: str, template: str, context: dict) -> bool:
        """Send email via SendGrid, AWS SES, etc."""
        # Implement based on your email provider
        pass
    
    def send_push(self, user_id: str, title: str, body: str, data: dict) -> bool:
        """Send push via Firebase, OneSignal, etc."""
        pass
    
    def send_sms(self, to: str, message: str) -> bool:
        """Send SMS via Twilio, AWS SNS, etc."""
        pass
```

---

## 3. Database Schema Creation

Create these MongoDB collections with sample data:

```javascript
// MongoDB shell or Atlas UI

// learning_plans collection
db.createCollection("learning_plans", {
  validator: {
    $jsonSchema: {
      bsonType: "object",
      required: ["user_id", "plan_title", "modules"],
      properties: {
        _id: { bsonType: "string" },
        user_id: { bsonType: "string" },
        plan_title: { bsonType: "string" },
        status: { enum: ["active", "completed", "archived", "paused"] },
        modules: { bsonType: "array" },
        created_at: { bsonType: "date" },
        updated_at: { bsonType: "date" }
      }
    }
  }
})

// user_progress collection
db.createCollection("user_progress", {
  validator: {
    $jsonSchema: {
      bsonType: "object",
      required: ["user_id", "plan_id"],
      properties: {
        _id: { bsonType: "string" },
        user_id: { bsonType: "string" },
        plan_id: { bsonType: "string" },
        completed_modules: { bsonType: "array" },
        total_hours_spent: { bsonType: "double" },
        created_at: { bsonType: "date" }
      }
    }
  }
})

// schedules collection
db.createCollection("schedules")

// reminders collection
db.createCollection("reminders")

// ical_tokens collection
db.createCollection("ical_tokens")
```

---

## 4. Testing the Integration

### Test 1: Create a Learning Plan

```bash
curl -X POST http://localhost:8000/api/v1/plans \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "goal": "Master agentic AI in 4 weeks",
    "skill_level": "intermediate",
    "hours_per_week": 5,
    "duration_weeks": 4,
    "topics": ["agent architectures", "tool use", "agentic loops"]
  }'
```

### Test 2: Get Plan

```bash
curl -X GET http://localhost:8000/api/v1/plans/{plan_id} \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Test 3: Mark Module Complete

```bash
curl -X PATCH http://localhost:8000/api/v1/plans/{plan_id}/modules/{module_id} \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "status": "completed",
    "time_spent_hours": 5.5,
    "quiz_score": 85
  }'
```

### Test 4: Export Calendar

```bash
curl -X GET "http://localhost:8000/api/v1/plans/{plan_id}/calendar.ics?token={ical_token}" \
  -o learning_plan.ics
```

### Test 5: Create Reminder

```bash
curl -X POST http://localhost:8000/api/v1/plans/{plan_id}/reminders \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "type": "email",
    "schedule": "every_sunday_19:00",
    "enabled": true
  }'
```

---

## 5. Environment Configuration

Add to your `.env` file:

```bash
# Planner settings
PLANNER_MODEL=gpt-4-turbo
PLANNER_TEMPERATURE=0.7

# Calendar
CALENDAR_TIMEZONE=UTC

# Reminder defaults
REMINDER_CHECK_INTERVAL=3600  # seconds (1 hour)

# Notification service
EMAIL_PROVIDER=sendgrid  # or: smtp, aws_ses
EMAIL_FROM=noreply@learnlab.io
NOTIFICATION_ENABLED=true
```

---

## 6. Running the Complete System

### Local Development

```bash
# Terminal 1: FastAPI backend
cd backend
python -m uvicorn main:app --reload

# Terminal 2: Celery worker
celery -A celery_app worker --loglevel=info

# Terminal 3: Celery Beat scheduler
celery -A celery_app beat --loglevel=info

# Terminal 4 (optional): Redis (if using Docker)
docker run -d -p 6379:6379 redis:latest
```

### Docker Compose

Add to your `docker-compose.yml`:

```yaml
celery-worker:
  build: .
  command: celery -A celery_app worker --loglevel=info
  depends_on:
    - redis
    - mongodb
  environment:
    - REDIS_URL=redis://redis:6379/0

celery-beat:
  build: .
  command: celery -A celery_app beat --loglevel=info
  depends_on:
    - redis
    - mongodb
  environment:
    - REDIS_URL=redis://redis:6379/0
```

---

## 7. Monitoring & Logging

### Check Celery Tasks

```bash
# View active tasks
celery -A celery_app inspect active

# View scheduled tasks
celery -A celery_app inspect scheduled

# View worker stats
celery -A celery_app inspect stats
```

### Monitor with Flower (optional)

```bash
# Install
pip install flower

# Run
celery -A celery_app flower --port=5555
```

Then visit: http://localhost:5555

---

## 8. Common Issues & Fixes

| Issue | Solution |
|-------|----------|
| **Reminders not sending** | Check Redis connection, Celery worker running, logs |
| **iCal export fails** | Ensure `icalendar` installed, plan has modules |
| **Plan generation timeout** | Increase LLM timeout, check OpenAI API quota |
| **Module not updating** | Verify user auth token, plan_id matches, DB indexes created |
| **Streak not calculating** | Ensure Celery Beat scheduler is running |

---

## 9. Next Phase (Phase 2b: Frontend)

Once backend is working, build React/Next.js components:

- Plan creation form
- Visual timeline/calendar
- Progress dashboard
- iCal sync buttons

See `PHASE2_PLANNER_CALENDAR.md` section 5 for component specs.

---

## 10. Rollout Checklist

- [ ] Files created in correct locations
- [ ] DBService updated with PlannerDBService
- [ ] MongoDB indexes created
- [ ] Celery + Redis configured
- [ ] Environment variables set
- [ ] API endpoints tested (curl or Postman)
- [ ] Reminders sending successfully
- [ ] Calendar export working
- [ ] Logging configured
- [ ] Documentation updated

---

## Questions?

Refer back to:
- `PHASE2_PLANNER_CALENDAR.md` — Design & architecture
- API route docstrings — Endpoint details
- `planner_agent.py` — Agent logic

Good luck! 🚀
