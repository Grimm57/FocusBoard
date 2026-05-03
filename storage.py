import json
import os
from datetime import date
from pathlib import Path


def _default_data_path():
    appdata = os.environ.get("APPDATA")
    if appdata:
        return Path(appdata) / "FocusBoard" / "data.json"
    return Path.home() / ".focusboard" / "data.json"


def _legacy_data_path():
    return Path(__file__).resolve().parent / "data" / "data.json"


DATA_PATH = _default_data_path()
LEGACY_DATA_PATH = _legacy_data_path()
DEFAULT_DATA = {
    "tasks": [],
    "focus_sessions": [],
    "task_completion_events": [],
    "daily_records": {},
    "last_active_date": date.today().isoformat(),
    "session_board": {"focus_task_id": None, "break_task_id": None, "break_label": "休息时间"},
    "settings": {"work_minutes": 25, "break_minutes": 5},
}


class Storage:
    def __init__(self, path=DATA_PATH):
        self.path = Path(path)
        self.legacy_path = LEGACY_DATA_PATH
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def load(self):
        source_path = self._resolve_source_path()
        if source_path is None:
            data = self._default_data()
            self.save(data)
            return data

        with source_path.open("r", encoding="utf-8") as file:
            data = json.load(file)

        merged = self._merge_defaults(data)
        if source_path != self.path:
            self.save(merged)
        return merged

    def save(self, data):
        with self.path.open("w", encoding="utf-8") as file:
            json.dump(data, file, ensure_ascii=False, indent=2)

    def _resolve_source_path(self):
        if self.path.exists():
            return self.path
        if self.legacy_path.exists():
            return self.legacy_path
        return None

    def _merge_defaults(self, data):
        merged = self._default_data()
        merged.update(data)
        merged["settings"] = DEFAULT_DATA["settings"].copy()
        merged["settings"].update(data.get("settings", {}))
        merged["daily_records"] = data.get("daily_records", {})
        merged["session_board"] = DEFAULT_DATA["session_board"].copy()
        merged["session_board"].update(data.get("session_board", {}))
        merged["focus_sessions"] = data.get("focus_sessions", [])
        merged["task_completion_events"] = data.get("task_completion_events", [])
        return merged

    def _default_data(self):
        return {
            "tasks": [],
            "focus_sessions": [],
            "task_completion_events": [],
            "daily_records": {},
            "last_active_date": date.today().isoformat(),
            "session_board": DEFAULT_DATA["session_board"].copy(),
            "settings": DEFAULT_DATA["settings"].copy(),
        }
