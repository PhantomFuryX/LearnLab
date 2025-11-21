"""
Celery tasks for managing learning plan reminders.
Integrate with your existing Celery app.
"""

from celery import shared_task
from datetime import datetime, timedelta
import logging
from typing import Optional

logger = logging.getLogger(__name__)


# ============================================================================
# REMINDER TASKS
# ============================================================================


@shared_task(bind=True, max_retries=3)
def send_reminder(self, reminder_id: str, user_id: str, plan_id: str):
    """
    Send a reminder to the user about their learning plan.

    Can be email, push notification, or SMS.
    """
    try:
        from services.db_service import DBService
        from services.notification_service import NotificationService

        db = DBService()
        notifier = NotificationService()

        # Fetch reminder config
        reminder = db.db["reminders"].find_one({"_id": reminder_id})
        if not reminder or not reminder.get("enabled"):
            logger.info(f"Reminder {reminder_id} not found or disabled")
            return

        # Fetch plan
        plan = db.get_learning_plan(plan_id)
        if not plan:
            logger.error(f"Plan {plan_id} not found")
            return

        # Fetch user
        user = db.db["users"].find_one({"_id": user_id})
        if not user:
            logger.error(f"User {user_id} not found")
            return

        # Get user's progress
        progress = db.get_user_progress(user_id, plan_id)

        # Build notification content
        notification = _build_reminder_notification(plan, progress)

        # Send based on reminder type
        reminder_type = reminder.get("type", "email")
        if reminder_type == "email":
            success = notifier.send_email(
                to=user.get("email"),
                subject=f"Learning Reminder: {plan.get('plan_title')}",
                template="learning_reminder",
                context=notification,
            )
        elif reminder_type == "push":
            success = notifier.send_push(
                user_id=user_id,
                title=notification.get("title"),
                body=notification.get("body"),
                data={"plan_id": plan_id},
            )
        elif reminder_type == "sms":
            success = notifier.send_sms(
                to=user.get("phone"),
                message=notification.get("body"),
            )
        else:
            logger.warning(f"Unknown reminder type: {reminder_type}")
            return

        if success:
            db.update_reminder_sent(reminder_id)
            logger.info(f"✓ Sent {reminder_type} reminder {reminder_id}")
        else:
            logger.error(f"Failed to send {reminder_type} reminder {reminder_id}")

    except Exception as exc:
        logger.error(f"Error sending reminder: {exc}")
        self.retry(exc=exc, countdown=60)  # Retry in 60 seconds


@shared_task
def check_and_send_reminders():
    """
    Periodic task: Check all active reminders and send those that are due.
    Schedule this to run hourly or as needed.
    """
    try:
        from services.db_service import DBService
        import dateparser

        db = DBService()
        reminders = db.get_active_reminders()

        now = datetime.utcnow()
        sent_count = 0

        for reminder in reminders:
            schedule = reminder.get("schedule")
            last_sent = reminder.get("last_sent")

            if _should_send_reminder(schedule, last_sent, now):
                send_reminder.delay(
                    reminder.get("_id"),
                    reminder.get("plan_id"),
                )
                sent_count += 1

        logger.info(f"✓ Checked reminders, sent {sent_count}")
        return {"checked": len(reminders), "sent": sent_count}

    except Exception as e:
        logger.error(f"Error checking reminders: {e}")
        return {"error": str(e)}


@shared_task
def calculate_user_streaks():
    """
    Periodic task: Update user streaks based on recent activity.
    Run daily (e.g., at midnight UTC).
    """
    try:
        from services.db_service import DBService

        db = DBService()
        progress_docs = list(db.db["user_progress"].find())

        updated_count = 0

        for progress in progress_docs:
            user_id = progress.get("user_id")
            plan_id = progress.get("plan_id")
            last_access = progress.get("last_access")

            if last_access:
                days_since = (datetime.utcnow() - last_access).days

                if days_since <= 1:
                    # User accessed plan today or yesterday, increment streak
                    new_streak = progress.get("streak_days", 0) + 1
                    db.update_streak(user_id, plan_id, new_streak)
                    updated_count += 1
                elif days_since > 7:
                    # Reset streak if inactive for >7 days
                    db.update_streak(user_id, plan_id, 0)
                    updated_count += 1

        logger.info(f"✓ Updated streaks for {updated_count} users")
        return {"updated": updated_count}

    except Exception as e:
        logger.error(f"Error calculating streaks: {e}")
        return {"error": str(e)}


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================


def _should_send_reminder(schedule: str, last_sent: Optional[datetime], now: datetime) -> bool:
    """
    Determine if a reminder should be sent based on its schedule.

    Supports:
    - Cron-like: "every_sunday_19:00"
    - ISO datetime: "2025-11-25T19:00:00"
    """
    try:
        if not schedule:
            return False

        # Handle cron-like patterns
        if schedule.startswith("every_"):
            return _check_cron_schedule(schedule, last_sent, now)

        # Handle ISO datetime (one-time)
        else:
            scheduled_time = datetime.fromisoformat(schedule)
            if now >= scheduled_time:
                if last_sent is None or last_sent < scheduled_time:
                    return True

        return False

    except Exception as e:
        logger.error(f"Error checking schedule: {e}")
        return False


def _check_cron_schedule(cron: str, last_sent: Optional[datetime], now: datetime) -> bool:
    """
    Check if a cron-like schedule is due.

    Examples:
    - "every_sunday_19:00" → Send every Sunday at 7 PM
    - "every_day_09:00" → Send every day at 9 AM
    - "every_monday_wednesday_18:00" → Send Mon/Wed at 6 PM
    """
    try:
        parts = cron.split("_")

        if len(parts) < 3:
            return False

        # Parse days
        days = parts[1:-1]  # All parts except "every" and time
        time_str = parts[-1]  # Last part is time

        # Parse target time
        target_hour, target_minute = map(int, time_str.split(":"))

        # Check if today is a target day
        day_name = now.strftime("%A").lower()
        if "day" not in days and day_name not in days:
            return False

        # Check if time has passed
        if now.hour < target_hour or (now.hour == target_hour and now.minute < target_minute):
            return False

        # Check if already sent today
        if last_sent:
            if last_sent.date() == now.date():
                return False

        return True

    except Exception as e:
        logger.error(f"Error parsing cron schedule: {e}")
        return False


def _build_reminder_notification(plan: dict, progress: dict) -> dict:
    """
    Build notification content for a learning plan reminder.
    """
    completed_modules = progress.get("completed_modules", [])
    total_modules = len(plan.get("modules", []))
    completion_pct = (len(completed_modules) / total_modules * 100) if total_modules > 0 else 0

    # Find next incomplete module
    next_module = None
    for module in plan.get("modules", []):
        if module.get("module_id") not in [m.get("module_id") for m in completed_modules]:
            next_module = module
            break

    next_module_title = next_module.get("title") if next_module else "Continue your learning"

    return {
        "title": f"Time to learn: {plan.get('plan_title')}",
        "body": f"You're {completion_pct:.0f}% through your learning plan. Next: {next_module_title}",
        "plan_title": plan.get("plan_title"),
        "completion_pct": completion_pct,
        "next_module": next_module_title,
        "hours_spent": progress.get("total_hours_spent", 0),
        "streak_days": progress.get("streak_days", 0),
    }


# ============================================================================
# CELERY BEAT SCHEDULE
# ============================================================================

# Add this to your Celery app configuration:
#
# app.conf.beat_schedule = {
#     'check-reminders-hourly': {
#         'task': 'tasks.reminder_tasks.check_and_send_reminders',
#         'schedule': crontab(minute=0),  # Every hour
#     },
#     'calculate-streaks-daily': {
#         'task': 'tasks.reminder_tasks.calculate_user_streaks',
#         'schedule': crontab(hour=0, minute=0),  # Every day at midnight UTC
#     },
# }
