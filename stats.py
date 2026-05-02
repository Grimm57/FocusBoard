from datetime import date, datetime, timedelta


def today_summary(data, target_date=None):
    today = target_date or datetime.now().date()
    completed_tasks = 0
    focus_minutes = 0
    pomodoro_count = 0

    for task in data.get("tasks", []):
        completed_at = task.get("completed_at")
        if task.get("completed") and completed_at:
            completed_day = datetime.fromisoformat(completed_at).date()
            if completed_day == today:
                completed_tasks += 1

    for session in data.get("focus_sessions", []):
        ended_at = session.get("ended_at")
        if session.get("mode") != "work" or not ended_at:
            continue

        session_day = datetime.fromisoformat(ended_at).date()
        if session_day == today:
            minutes = int(session.get("duration_minutes", 0))
            focus_minutes += minutes
            pomodoro_count += 1

    return {
        "completed_tasks": completed_tasks,
        "focus_minutes": focus_minutes,
        "pomodoro_count": pomodoro_count,
    }


def build_daily_record(data, target_date):
    summary = today_summary(data, target_date=target_date)
    return {
        "completed_tasks": summary["completed_tasks"],
        "focus_minutes": summary["focus_minutes"],
        "pomodoro_count": summary["pomodoro_count"],
    }


def historical_summary(data):
    records = data.get("daily_records", {})
    total_completed_tasks = 0
    total_focus_minutes = 0
    total_pomodoro_count = 0

    for record in records.values():
        total_completed_tasks += int(record.get("completed_tasks", 0))
        total_focus_minutes += int(record.get("focus_minutes", 0))
        total_pomodoro_count += int(record.get("pomodoro_count", 0))

    today = today_summary(data)
    total_completed_tasks += today["completed_tasks"]
    total_focus_minutes += today["focus_minutes"]
    total_pomodoro_count += today["pomodoro_count"]

    return {
        "total_completed_tasks": total_completed_tasks,
        "total_focus_minutes": total_focus_minutes,
        "total_pomodoro_count": total_pomodoro_count,
    }


def recent_daily_records(data, days=7):
    today = date.today()
    records = data.get("daily_records", {})
    items = []

    for offset in range(days - 1, -1, -1):
        current_day = today - timedelta(days=offset)
        current_key = current_day.isoformat()
        if current_key == today.isoformat():
            record = today_summary(data, target_date=current_day)
        else:
            record = records.get(
                current_key,
                {"completed_tasks": 0, "focus_minutes": 0, "pomodoro_count": 0},
            )
        items.append(
            {
                "date": current_key,
                "label": current_day.strftime("%m-%d"),
                "completed_tasks": int(record.get("completed_tasks", 0)),
                "focus_minutes": int(record.get("focus_minutes", 0)),
                "pomodoro_count": int(record.get("pomodoro_count", 0)),
            }
        )

    return items
