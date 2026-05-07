from datetime import datetime


class PomodoroTimer:
    def __init__(self, work_minutes=25, break_minutes=5):
        self.work_minutes = work_minutes
        self.break_minutes = break_minutes
        self.mode = "work"
        self.is_running = False
        self.remaining_seconds = work_minutes * 60
        self.session_started_at = None

    def start(self):
        if self.is_running:
            return
        self.is_running = True
        if self.session_started_at is None and self.mode == "work":
            self.session_started_at = datetime.now()

    def pause(self):
        self.is_running = False

    def reset(self):
        self.is_running = False
        self.mode = "work"
        self.remaining_seconds = self.work_minutes * 60
        self.session_started_at = None

    def switch_to_work(self):
        self.is_running = False
        self.mode = "work"
        self.remaining_seconds = self.work_minutes * 60
        self.session_started_at = None

    def switch_to_break(self):
        self.is_running = False
        self.mode = "break"
        self.remaining_seconds = self.break_minutes * 60
        self.session_started_at = None

    def update_durations(self, work_minutes, break_minutes):
        self.work_minutes = work_minutes
        self.break_minutes = break_minutes
        self.is_running = False
        self.session_started_at = None
        if self.mode == "work":
            self.remaining_seconds = self.work_minutes * 60
        else:
            self.remaining_seconds = self.break_minutes * 60

    def tick(self):
        if not self.is_running:
            return None

        if self.remaining_seconds > 0:
            self.remaining_seconds -= 1
            return None

        completed_mode = self.mode
        completed_started_at = self.session_started_at
        self.is_running = False

        if self.mode == "work":
            self.mode = "break"
            self.remaining_seconds = self.break_minutes * 60
            self.session_started_at = None
        else:
            self.mode = "work"
            self.remaining_seconds = self.work_minutes * 60
            self.session_started_at = None

        return {
            "completed_mode": completed_mode,
            "started_at": completed_started_at,
            "ended_at": datetime.now(),
            "duration_minutes": self.work_minutes if completed_mode == "work" else self.break_minutes,
        }

    def formatted_time(self):
        minutes, seconds = divmod(self.remaining_seconds, 60)
        return f"{minutes:02d}:{seconds:02d}"

    def mode_label(self):
        return "专注中" if self.mode == "work" else "休息中"
