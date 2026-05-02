import json
from datetime import date
from pathlib import Path


DATA_PATH = Path(__file__).resolve().parent / "data" / "data.json"
DEFAULT_DATA = {
    "tasks": [],
    "focus_sessions": [],
    "daily_records": {},
    "last_active_date": date.today().isoformat(),
    "session_board": {"focus_task_id": None, "break_task_id": None, "break_label": "休息时间"},
    "settings": {"work_minutes": 25, "break_minutes": 5},
}


class Storage:
    def __init__(self, path=DATA_PATH):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def load(self):
        if not self.path.exists():
            data = self._default_data()
            self.save(data)
            return data

        with self.path.open("r", encoding="utf-8") as file:
            data = json.load(file)

        return self._merge_defaults(data)

    def save(self, data):
        with self.path.open("w", encoding="utf-8") as file:
            json.dump(data, file, ensure_ascii=False, indent=2)

    def _merge_defaults(self, data):
        merged = self._default_data()
        merged.update(data)
        merged["settings"] = DEFAULT_DATA["settings"].copy()
        merged["settings"].update(data.get("settings", {}))
        merged["daily_records"] = data.get("daily_records", {})
        merged["session_board"] = DEFAULT_DATA["session_board"].copy()
        merged["session_board"].update(data.get("session_board", {}))
        return merged

    def _default_data(self):
        return {
            "tasks": [],
            "focus_sessions": [],
            "daily_records": {},
            "last_active_date": date.today().isoformat(),
            "session_board": DEFAULT_DATA["session_board"].copy(),
            "settings": DEFAULT_DATA["settings"].copy(),
        }
