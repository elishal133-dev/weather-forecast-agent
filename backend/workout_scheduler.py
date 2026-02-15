"""
Workout Scheduler - Calendar, Notifications, Weekly Summary
Manages scheduled workouts, sends reminders, generates reports.
"""

import json
import logging
from dataclasses import dataclass
from datetime import datetime, date, timedelta, time
from enum import Enum
from pathlib import Path
from typing import List, Optional, Dict, Any

logger = logging.getLogger('workout_scheduler')


class DayOfWeek(str, Enum):
    MONDAY = "monday"
    TUESDAY = "tuesday"
    WEDNESDAY = "wednesday"
    THURSDAY = "thursday"
    FRIDAY = "friday"
    SATURDAY = "saturday"
    SUNDAY = "sunday"


DAY_MAP = {
    0: DayOfWeek.MONDAY,
    1: DayOfWeek.TUESDAY,
    2: DayOfWeek.WEDNESDAY,
    3: DayOfWeek.THURSDAY,
    4: DayOfWeek.FRIDAY,
    5: DayOfWeek.SATURDAY,
    6: DayOfWeek.SUNDAY,
}

DAY_NAMES_HE = {
    DayOfWeek.MONDAY: "שני",
    DayOfWeek.TUESDAY: "שלישי",
    DayOfWeek.WEDNESDAY: "רביעי",
    DayOfWeek.THURSDAY: "חמישי",
    DayOfWeek.FRIDAY: "שישי",
    DayOfWeek.SATURDAY: "שבת",
    DayOfWeek.SUNDAY: "ראשון",
}

DAY_INDEX = {
    DayOfWeek.MONDAY: 0,
    DayOfWeek.TUESDAY: 1,
    DayOfWeek.WEDNESDAY: 2,
    DayOfWeek.THURSDAY: 3,
    DayOfWeek.FRIDAY: 4,
    DayOfWeek.SATURDAY: 5,
    DayOfWeek.SUNDAY: 6,
}


@dataclass
class ScheduledWorkout:
    """A recurring or one-time scheduled workout"""
    id: str
    day: DayOfWeek
    time_of_day: str  # "HH:MM" format
    workout_type: str
    duration_minutes: int = 30
    target_muscles: Optional[List[str]] = None
    recurring: bool = True
    active: bool = True
    notify_before_minutes: int = 30
    label: str = ""


class WorkoutScheduler:
    """Manages workout schedule and notifications"""

    def __init__(self, data_dir: str = "/tmp/workout_data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.schedule: List[Dict[str, Any]] = []
        self.notifications: List[Dict[str, Any]] = []
        self._load_data()

    def _load_data(self):
        """Load persisted schedule"""
        schedule_file = self.data_dir / "schedule.json"
        notifications_file = self.data_dir / "notifications.json"

        if schedule_file.exists():
            try:
                with open(schedule_file) as f:
                    self.schedule = json.load(f)
                logger.info(f"Loaded {len(self.schedule)} scheduled workouts")
            except Exception as e:
                logger.error(f"Error loading schedule: {e}")

        if notifications_file.exists():
            try:
                with open(notifications_file) as f:
                    self.notifications = json.load(f)
            except Exception as e:
                logger.error(f"Error loading notifications: {e}")

    def _save_schedule(self):
        """Persist schedule to disk"""
        try:
            with open(self.data_dir / "schedule.json", "w") as f:
                json.dump(self.schedule, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving schedule: {e}")

    def _save_notifications(self):
        """Persist notifications"""
        try:
            with open(self.data_dir / "notifications.json", "w") as f:
                json.dump(self.notifications, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving notifications: {e}")

    def add_scheduled_workout(
        self,
        day: str,
        time_of_day: str,
        workout_type: str,
        duration_minutes: int = 30,
        target_muscles: Optional[List[str]] = None,
        recurring: bool = True,
        notify_before_minutes: int = 30,
        label: str = ""
    ) -> Dict[str, Any]:
        """Add a workout to the schedule"""
        import uuid

        # Validate day
        try:
            day_enum = DayOfWeek(day.lower())
        except ValueError:
            raise ValueError(f"Invalid day: {day}. Use: {[d.value for d in DayOfWeek]}")

        # Validate time format
        try:
            parts = time_of_day.split(":")
            hour, minute = int(parts[0]), int(parts[1])
            if not (0 <= hour <= 23 and 0 <= minute <= 59):
                raise ValueError()
        except (ValueError, IndexError):
            raise ValueError("Invalid time format. Use HH:MM (e.g., '07:00')")

        entry = {
            "id": str(uuid.uuid4())[:8],
            "day": day_enum.value,
            "day_he": DAY_NAMES_HE[day_enum],
            "time_of_day": time_of_day,
            "workout_type": workout_type,
            "duration_minutes": duration_minutes,
            "target_muscles": target_muscles or [],
            "recurring": recurring,
            "active": True,
            "notify_before_minutes": notify_before_minutes,
            "label": label or f"{workout_type} workout",
            "created_at": datetime.now().isoformat()
        }

        self.schedule.append(entry)
        self._save_schedule()
        logger.info(f"Added scheduled workout on {day} at {time_of_day}")
        return entry

    def remove_scheduled_workout(self, schedule_id: str) -> bool:
        """Remove a scheduled workout"""
        for i, s in enumerate(self.schedule):
            if s["id"] == schedule_id:
                self.schedule.pop(i)
                self._save_schedule()
                return True
        return False

    def toggle_scheduled_workout(self, schedule_id: str) -> Optional[Dict]:
        """Toggle a scheduled workout active/inactive"""
        for s in self.schedule:
            if s["id"] == schedule_id:
                s["active"] = not s["active"]
                self._save_schedule()
                return s
        return None

    def get_schedule(self, active_only: bool = True) -> List[Dict]:
        """Get the full workout schedule"""
        result = self.schedule
        if active_only:
            result = [s for s in result if s.get("active", True)]

        # Sort by day of week then time
        def sort_key(s):
            try:
                day_idx = DAY_INDEX.get(DayOfWeek(s["day"]), 7)
            except ValueError:
                day_idx = 7
            return (day_idx, s.get("time_of_day", "00:00"))

        return sorted(result, key=sort_key)

    def get_todays_workouts(self) -> List[Dict]:
        """Get workouts scheduled for today"""
        today = DAY_MAP.get(date.today().weekday())
        if not today:
            return []
        return [
            s for s in self.schedule
            if s.get("active", True) and s.get("day") == today.value
        ]

    def get_upcoming_workouts(self, days: int = 7) -> List[Dict]:
        """Get upcoming workouts for the next N days"""
        upcoming = []
        today = date.today()

        for i in range(days):
            target_date = today + timedelta(days=i)
            day_enum = DAY_MAP.get(target_date.weekday())
            if not day_enum:
                continue

            for s in self.schedule:
                if s.get("active", True) and s.get("day") == day_enum.value:
                    upcoming.append({
                        **s,
                        "scheduled_date": target_date.isoformat(),
                        "is_today": i == 0,
                        "days_until": i
                    })

        return upcoming

    def get_calendar_view(self, weeks: int = 4) -> Dict[str, Any]:
        """Get a calendar view of scheduled and completed workouts"""
        today = date.today()
        # Start from the current week's Monday
        current_monday = today - timedelta(days=today.weekday())

        calendar = []
        for week_offset in range(weeks):
            week_start = current_monday + timedelta(weeks=week_offset)
            week = {
                "week_start": week_start.isoformat(),
                "days": []
            }

            for day_offset in range(7):
                target_date = week_start + timedelta(days=day_offset)
                day_enum = DAY_MAP.get(target_date.weekday())

                scheduled = [
                    s for s in self.schedule
                    if s.get("active", True) and s.get("day") == day_enum.value
                ] if day_enum else []

                week["days"].append({
                    "date": target_date.isoformat(),
                    "day": day_enum.value if day_enum else "",
                    "day_he": DAY_NAMES_HE.get(day_enum, "") if day_enum else "",
                    "is_today": target_date == today,
                    "is_past": target_date < today,
                    "scheduled_workouts": scheduled
                })

            calendar.append(week)

        return {
            "today": today.isoformat(),
            "weeks": calendar
        }

    # ============ Notifications ============

    def check_notifications(self) -> List[Dict[str, Any]]:
        """Check if any workout notifications should fire now"""
        now = datetime.now()
        today = DAY_MAP.get(now.weekday())
        if not today:
            return []

        pending = []
        for s in self.schedule:
            if not s.get("active", True) or s.get("day") != today.value:
                continue

            try:
                parts = s["time_of_day"].split(":")
                workout_time = now.replace(
                    hour=int(parts[0]), minute=int(parts[1]), second=0, microsecond=0
                )
            except (ValueError, IndexError):
                continue

            notify_minutes = s.get("notify_before_minutes", 30)
            notify_time = workout_time - timedelta(minutes=notify_minutes)

            # Check if we should notify (within a 5-minute window)
            if notify_time <= now <= notify_time + timedelta(minutes=5):
                # Check if already notified today
                already_notified = any(
                    n.get("schedule_id") == s["id"] and
                    n.get("date") == now.date().isoformat()
                    for n in self.notifications
                )

                if not already_notified:
                    notification = {
                        "schedule_id": s["id"],
                        "date": now.date().isoformat(),
                        "time": now.isoformat(),
                        "title": "Workout Reminder",
                        "title_he": "תזכורת אימון",
                        "body": f"{s.get('label', 'Workout')} at {s['time_of_day']}",
                        "body_he": f"{s.get('label', 'אימון')} ב-{s['time_of_day']}",
                        "workout_type": s.get("workout_type"),
                        "minutes_until": notify_minutes
                    }
                    pending.append(notification)
                    self.notifications.append(notification)
                    self._save_notifications()

        return pending

    def get_pending_notifications(self) -> List[Dict]:
        """Get today's upcoming notifications"""
        now = datetime.now()
        today_str = now.date().isoformat()
        today = DAY_MAP.get(now.weekday())
        if not today:
            return []

        pending = []
        for s in self.schedule:
            if not s.get("active", True) or s.get("day") != today.value:
                continue

            try:
                parts = s["time_of_day"].split(":")
                workout_time = now.replace(
                    hour=int(parts[0]), minute=int(parts[1]), second=0, microsecond=0
                )
            except (ValueError, IndexError):
                continue

            if workout_time > now:
                delta = workout_time - now
                pending.append({
                    "schedule_id": s["id"],
                    "label": s.get("label", "Workout"),
                    "time": s["time_of_day"],
                    "workout_type": s.get("workout_type"),
                    "minutes_until": int(delta.total_seconds() / 60),
                    "already_notified": any(
                        n.get("schedule_id") == s["id"] and
                        n.get("date") == today_str
                        for n in self.notifications
                    )
                })

        return pending

    def get_notification_history(self, limit: int = 20) -> List[Dict]:
        """Get recent notification history"""
        return sorted(
            self.notifications,
            key=lambda n: n.get("time", ""),
            reverse=True
        )[:limit]


# ============ Weekly Summary Generator ============

def generate_weekly_summary_text(summary: Dict[str, Any]) -> Dict[str, str]:
    """Generate a formatted weekly summary text"""

    total = summary["total_workouts"]
    duration = summary["total_duration_minutes"]
    calories = summary["total_calories"]
    goal = summary.get("goal_progress", "N/A")
    goal_met = summary.get("goal_met", False)
    streak = summary.get("streak_days", 0)
    by_type = summary.get("workouts_by_type", {})
    muscles = summary.get("muscle_groups_hit", {})
    rating = summary.get("avg_rating")
    days = summary.get("workout_days", [])

    # English version
    lines_en = [
        f"Weekly Workout Summary ({summary['week_start']} to {summary['week_end']})",
        "=" * 50,
        f"Total Workouts: {total} ({goal})",
        f"Goal Status: {'Met' if goal_met else 'Not Met'}",
        f"Total Duration: {duration} minutes",
        f"Calories Burned: {calories}",
        f"Current Streak: {streak} days",
    ]

    if by_type:
        lines_en.append("\nWorkout Types:")
        for t, count in by_type.items():
            lines_en.append(f"  - {t}: {count}")

    if muscles:
        top_muscles = sorted(muscles.items(), key=lambda x: x[1], reverse=True)[:5]
        lines_en.append("\nMost Trained Muscle Groups:")
        for m, count in top_muscles:
            lines_en.append(f"  - {m}: {count} exercises")

    if days:
        lines_en.append(f"\nActive Days: {', '.join(days)}")

    if rating:
        lines_en.append(f"Average Satisfaction: {rating}/5")

    # Motivational note
    if goal_met:
        lines_en.append("\nGreat job hitting your weekly goal!")
    elif total > 0:
        lines_en.append(f"\nKeep going - you're {total} workout(s) into your goal!")
    else:
        lines_en.append("\nNew week, fresh start! Let's get moving!")

    # Hebrew version
    type_names_he = {
        "strength": "כוח",
        "cardio": "אירובי",
        "hiit": "HIIT",
        "flexibility": "גמישות",
        "mixed": "משולב"
    }

    lines_he = [
        f"סיכום אימונים שבועי ({summary['week_start']} עד {summary['week_end']})",
        "=" * 50,
        f"סה\"כ אימונים: {total} ({goal})",
        f"יעד שבועי: {'הושג' if goal_met else 'לא הושג'}",
        f"זמן כולל: {duration} דקות",
        f"קלוריות: {calories}",
        f"רצף נוכחי: {streak} ימים",
    ]

    if by_type:
        lines_he.append("\nסוגי אימון:")
        for t, count in by_type.items():
            t_he = type_names_he.get(t, t)
            lines_he.append(f"  - {t_he}: {count}")

    if goal_met:
        lines_he.append("\nכל הכבוד! השגת את היעד השבועי!")
    elif total > 0:
        lines_he.append(f"\nהמשך כך - עשית {total} אימונים עד כה!")
    else:
        lines_he.append("\nשבוע חדש, התחלה חדשה! בוא נתחיל!")

    return {
        "text_en": "\n".join(lines_en),
        "text_he": "\n".join(lines_he),
        "summary": summary
    }


# Module-level instance
workout_scheduler = WorkoutScheduler()
