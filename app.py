import tkinter as tk
from ctypes import windll
from datetime import date, datetime, timedelta
from tkinter import messagebox, ttk
from uuid import uuid4

from pomodoro import PomodoroTimer
from stats import build_daily_record, historical_summary, recent_daily_records, task_session_counts, today_summary
from storage import Storage


THEMES = {
    "light": {
        "app_bg": "#eef2ff",
        "card_bg": "#ffffff",
        "section_bg": "#f8fafc",
        "header_bg": "#4f46e5",
        "header_subtle": "#dbeafe",
        "header_text": "#ffffff",
        "text": "#111827",
        "muted_text": "#6b7280",
        "secondary_text": "#475569",
        "border": "#e5e7eb",
        "slot_border": "#e2e8f0",
        "selected_bg": "#ede9fe",
        "focus_active_bg": "#f5f3ff",
        "focus_active_border": "#7c3aed",
        "focus_active_text": "#7c3aed",
        "break_active_bg": "#eff6ff",
        "break_active_border": "#0ea5e9",
        "break_active_text": "#0284c7",
        "timer_badge_bg": "#eef2ff",
        "timer_badge_text": "#4338ca",
    },
    "dark": {
        "app_bg": "#0f172a",
        "card_bg": "#111827",
        "section_bg": "#1f2937",
        "header_bg": "#312e81",
        "header_subtle": "#c7d2fe",
        "header_text": "#f8fafc",
        "text": "#f8fafc",
        "muted_text": "#94a3b8",
        "secondary_text": "#cbd5e1",
        "border": "#374151",
        "slot_border": "#475569",
        "selected_bg": "#312e81",
        "focus_active_bg": "#2e1065",
        "focus_active_border": "#a78bfa",
        "focus_active_text": "#c4b5fd",
        "break_active_bg": "#082f49",
        "break_active_border": "#38bdf8",
        "break_active_text": "#7dd3fc",
        "timer_badge_bg": "#1e293b",
        "timer_badge_text": "#c4b5fd",
    },
}


class TaskBoardApp:
    def __init__(self):
        self.storage = Storage()
        self.data = self.storage.load()
        self._rollover_day_if_needed()
        self._ensure_task_defaults()
        settings = self.data["settings"]
        self.timer = PomodoroTimer(
            work_minutes=settings.get("work_minutes", 25),
            break_minutes=settings.get("break_minutes", 5),
        )

        self.root = tk.Tk()
        self.root.title("今日任务展板")
        self.root.geometry("560x820")
        self.root.resizable(False, False)

        self.task_title_var = tk.StringVar()
        self.task_type_var = tk.StringVar(value="focus")
        self.date_text_var = tk.StringVar()
        self.time_text_var = tk.StringVar()
        self.timer_text_var = tk.StringVar(value=self.timer.formatted_time())
        self.timer_mode_var = tk.StringVar(value=self.timer.mode_label())
        self.focus_slot_title_var = tk.StringVar()
        self.focus_slot_hint_var = tk.StringVar()
        self.break_slot_title_var = tk.StringVar()
        self.break_slot_hint_var = tk.StringVar()
        self.completed_tasks_var = tk.StringVar()
        self.focus_minutes_var = tk.StringVar()
        self.pomodoro_count_var = tk.StringVar()
        self.total_completed_tasks_var = tk.StringVar()
        self.total_focus_minutes_var = tk.StringVar()
        self.total_pomodoro_count_var = tk.StringVar()

        self.selected_task_id = None
        self.tasks_collapsed = False

        self._build_ui()
        self._apply_theme()
        self._bind_mousewheel()
        self._update_clock()
        self.refresh_task_list()
        self.refresh_slots()
        self.refresh_stats()
        self.refresh_history()
        self._schedule_tick()

    def _theme_colors(self):
        theme_name = self.data.get("settings", {}).get("theme", "light")
        return THEMES.get(theme_name, THEMES["light"])

    def _build_ui(self):
        self.style = ttk.Style()
        self.style.theme_use("clam")
        self.style.configure("Primary.TButton", font=("Microsoft YaHei UI", 10, "bold"))
        self.style.configure("Ghost.TButton", font=("Microsoft YaHei UI", 9))

        self.shell = tk.Frame(self.root)
        self.shell.pack(fill="both", expand=True)

        self.canvas = tk.Canvas(self.shell, highlightthickness=0)
        self.canvas.pack(side="left", fill="both", expand=True)

        self.scrollbar = ttk.Scrollbar(self.shell, orient="vertical", command=self.canvas.yview)
        self.scrollbar.pack(side="right", fill="y")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.content_frame = tk.Frame(self.canvas, padx=16, pady=16)
        self.canvas_window = self.canvas.create_window((0, 0), window=self.content_frame, anchor="nw")
        self.content_frame.bind("<Configure>", self._on_content_configure)
        self.canvas.bind("<Configure>", self._on_canvas_configure)

        self._build_header(self.content_frame)
        self._build_tasks_card(self.content_frame)
        self._build_timer_card(self.content_frame)
        self._build_stats_card(self.content_frame)
        self._build_history_card(self.content_frame)

    def _build_header(self, parent):
        self.header_card = tk.Frame(parent, padx=18, pady=18)
        self.header_card.pack(fill="x", pady=(0, 12))

        header_top = tk.Frame(self.header_card)
        header_top.pack(fill="x")
        self.header_title_label = tk.Label(
            header_top,
            text="每日任务小展板",
            font=("Microsoft YaHei UI", 18, "bold"),
        )
        self.header_title_label.pack(side="left", anchor="w")
        ttk.Button(header_top, text="设置", command=self.open_settings_dialog, style="Ghost.TButton").pack(side="right")

        self.header_info_row = tk.Frame(self.header_card)
        self.header_info_row.pack(anchor="w", pady=(6, 0))
        self.date_label = tk.Label(self.header_info_row, textvariable=self.date_text_var, font=("Microsoft YaHei UI", 10))
        self.date_label.pack(side="left")
        self.header_spacer_label = tk.Label(self.header_info_row, text="  ", font=("Microsoft YaHei UI", 10))
        self.header_spacer_label.pack(side="left")
        self.time_label = tk.Label(self.header_info_row, textvariable=self.time_text_var, font=("Consolas", 11, "bold"))
        self.time_label.pack(side="left")

    def _build_tasks_card(self, parent):
        self.tasks_card = ttk.Frame(parent, style="Card.TFrame", padding=16)
        self.tasks_card.pack(fill="x", pady=(0, 12))

        self.tasks_header_row = tk.Frame(self.tasks_card)
        self.tasks_header_row.pack(fill="x")
        ttk.Label(self.tasks_header_row, text="任务列表", style="Section.TLabel").pack(side="left")
        self.tasks_toggle_button = ttk.Button(self.tasks_header_row, text="收起", command=self.toggle_tasks_collapsed, style="Ghost.TButton")
        self.tasks_toggle_button.pack(side="right")

        self.tasks_action_row = tk.Frame(self.tasks_card)
        self.tasks_action_row.pack(fill="x", pady=(10, 0))
        ttk.Button(self.tasks_action_row, text="放入当前专注", command=self.assign_selected_task_to_focus, style="Primary.TButton").pack(side="left")
        ttk.Button(self.tasks_action_row, text="放入休息槽位", command=self.assign_selected_task_to_break, style="Primary.TButton").pack(side="left", padx=(8, 0))

        self.tasks_input_row = tk.Frame(self.tasks_card)
        self.tasks_input_row.pack(fill="x", pady=(12, 10))

        entry = ttk.Entry(self.tasks_input_row, textvariable=self.task_title_var, font=("Microsoft YaHei UI", 11))
        entry.pack(side="left", fill="x", expand=True)
        entry.bind("<Return>", lambda event: self.add_task())

        task_type_box = ttk.Combobox(self.tasks_input_row, textvariable=self.task_type_var, values=["focus", "break"], state="readonly", width=8)
        task_type_box.pack(side="left", padx=(8, 0))

        ttk.Button(self.tasks_input_row, text="添加", command=self.add_task, style="Primary.TButton").pack(side="left", padx=(8, 0))

        self.tasks_help_label = ttk.Label(self.tasks_card, text="点击任务可选中，再放入专注槽位或休息槽位。", style="Muted.TLabel")
        self.tasks_help_label.pack(anchor="w", pady=(0, 8))

        self.task_sections_frame = tk.Frame(self.tasks_card)
        self.task_sections_frame.pack(fill="x")

        self.focus_tasks_card = self._build_task_section(self.task_sections_frame, "专注任务")
        self.focus_tasks_card["wrapper"].pack(side="left", fill="both", expand=True)
        self.break_tasks_card = self._build_task_section(self.task_sections_frame, "休息任务")
        self.break_tasks_card["wrapper"].pack(side="left", fill="both", expand=True, padx=(10, 0))

        self.focus_tasks_frame = self.focus_tasks_card["body"]
        self.break_tasks_frame = self.break_tasks_card["body"]

    def _build_task_section(self, parent, title):
        wrapper = tk.Frame(parent, padx=10, pady=10, highlightthickness=1)
        title_label = tk.Label(wrapper, text=title, font=("Microsoft YaHei UI", 10, "bold"))
        title_label.pack(anchor="w", pady=(0, 8))
        body = tk.Frame(wrapper)
        body.pack(fill="both", expand=True)
        return {"wrapper": wrapper, "body": body, "title": title_label}

    def _build_timer_card(self, parent):
        self.timer_card = ttk.Frame(parent, style="Card.TFrame", padding=16)
        self.timer_card.pack(fill="x", pady=(0, 12))

        ttk.Label(self.timer_card, text="番茄专注", style="Section.TLabel").pack(anchor="w")

        self.timer_mode_label = tk.Label(self.timer_card, textvariable=self.timer_mode_var, font=("Microsoft YaHei UI", 10, "bold"), padx=12, pady=6)
        self.timer_mode_label.pack(anchor="w", pady=(10, 8))

        self.slots_row = tk.Frame(self.timer_card)
        self.slots_row.pack(fill="x", pady=(0, 12))

        self.focus_slot_frame = self._build_slot_card(self.slots_row, "当前专注槽位", self.focus_slot_title_var, self.focus_slot_hint_var)
        self.focus_slot_frame.pack(side="left", expand=True, fill="both")
        self._bind_slot_click(self.focus_slot_frame, self.switch_to_work)
        self.break_slot_frame = self._build_slot_card(self.slots_row, "休息槽位", self.break_slot_title_var, self.break_slot_hint_var)
        self.break_slot_frame.pack(side="left", expand=True, fill="both", padx=(10, 0))
        self._bind_slot_click(self.break_slot_frame, self.switch_to_break)

        self.timer_value_label = tk.Label(self.timer_card, textvariable=self.timer_text_var, font=("Consolas", 34, "bold"))
        self.timer_value_label.pack(anchor="center", pady=(2, 12))

        self.timer_button_row = tk.Frame(self.timer_card)
        self.timer_button_row.pack(fill="x")

        ttk.Button(self.timer_button_row, text="开始", command=self.start_timer, style="Primary.TButton").pack(side="left", expand=True, fill="x")
        ttk.Button(self.timer_button_row, text="暂停", command=self.pause_timer).pack(side="left", expand=True, fill="x", padx=8)
        ttk.Button(self.timer_button_row, text="重置", command=self.reset_timer).pack(side="left", expand=True, fill="x")

    def _build_slot_card(self, parent, title, primary_var, secondary_var):
        frame = tk.Frame(parent, padx=12, pady=12, highlightthickness=2)
        tk.Label(frame, text=title, font=("Microsoft YaHei UI", 10, "bold")).pack(anchor="w")
        tk.Label(frame, textvariable=primary_var, font=("Microsoft YaHei UI", 11, "bold"), wraplength=180, justify="left").pack(anchor="w", pady=(10, 4))
        tk.Label(frame, textvariable=secondary_var, font=("Microsoft YaHei UI", 9), wraplength=180, justify="left").pack(anchor="w")
        return frame

    def _build_stats_card(self, parent):
        self.stats_card = ttk.Frame(parent, style="Card.TFrame", padding=16)
        self.stats_card.pack(fill="x", pady=(0, 12))

        ttk.Label(self.stats_card, text="今日统计", style="Section.TLabel").pack(anchor="w")

        self.stats_grid = tk.Frame(self.stats_card)
        self.stats_grid.pack(fill="x", pady=(12, 0))

        self._build_stat_tile(self.stats_grid, "完成次数", self.completed_tasks_var, 0, 0)
        self._build_stat_tile(self.stats_grid, "专注时长", self.focus_minutes_var, 0, 1)
        self._build_stat_tile(self.stats_grid, "完成番茄", self.pomodoro_count_var, 1, 0)
        self._build_stat_tile(self.stats_grid, "累计完成", self.total_completed_tasks_var, 1, 1)

    def _build_history_card(self, parent):
        self.history_card = ttk.Frame(parent, style="Card.TFrame", padding=16)
        self.history_card.pack(fill="both", expand=True)

        ttk.Label(self.history_card, text="历史统计", style="Section.TLabel").pack(anchor="w")

        self.history_summary_row = tk.Frame(self.history_card)
        self.history_summary_row.pack(fill="x", pady=(12, 12))

        self._build_history_summary_item(self.history_summary_row, "累计专注", self.total_focus_minutes_var).pack(side="left", expand=True, fill="x")
        self._build_history_summary_item(self.history_summary_row, "累计番茄", self.total_pomodoro_count_var).pack(side="left", expand=True, fill="x", padx=8)

        self.history_table_header = tk.Frame(self.history_card, padx=10, pady=8)
        self.history_table_header.pack(fill="x")
        tk.Label(self.history_table_header, text="日期", font=("Microsoft YaHei UI", 9, "bold"), width=8, anchor="w").grid(row=0, column=0, sticky="w")
        tk.Label(self.history_table_header, text="完成", font=("Microsoft YaHei UI", 9, "bold"), width=10, anchor="w").grid(row=0, column=1, sticky="w", padx=(16, 0))
        tk.Label(self.history_table_header, text="专注", font=("Microsoft YaHei UI", 9, "bold"), width=12, anchor="w").grid(row=0, column=2, sticky="w", padx=(16, 0))

        self.history_frame = tk.Frame(self.history_card)
        self.history_frame.pack(fill="both", expand=True, pady=(8, 0))

    def _build_stat_tile(self, parent, label, variable, row, column):
        colors = self._theme_colors()
        tile = tk.Frame(parent, bg=colors["section_bg"], padx=12, pady=12)
        tile.grid(row=row, column=column, sticky="nsew", padx=4, pady=4)
        parent.grid_columnconfigure(column, weight=1)
        tk.Label(tile, text=label, font=("Microsoft YaHei UI", 10), bg=colors["section_bg"], fg=colors["secondary_text"]).pack(anchor="w")
        tk.Label(tile, textvariable=variable, font=("Microsoft YaHei UI", 14, "bold"), bg=colors["section_bg"], fg=colors["text"]).pack(anchor="w", pady=(6, 0))

    def _build_history_summary_item(self, parent, label, variable):
        colors = self._theme_colors()
        frame = tk.Frame(parent, bg=colors["section_bg"], padx=12, pady=12)
        tk.Label(frame, text=label, font=("Microsoft YaHei UI", 10), bg=colors["section_bg"], fg=colors["secondary_text"]).pack(anchor="w")
        tk.Label(frame, textvariable=variable, font=("Microsoft YaHei UI", 13, "bold"), bg=colors["section_bg"], fg=colors["text"]).pack(anchor="w", pady=(4, 0))
        return frame

    def open_settings_dialog(self):
        dialog = tk.Toplevel(self.root)
        dialog.title("设置")
        dialog.resizable(False, False)
        dialog.transient(self.root)
        dialog.grab_set()

        colors = self._theme_colors()
        dialog.configure(bg=colors["card_bg"])

        theme_var = tk.StringVar(value=self.data["settings"].get("theme", "light"))
        work_var = tk.StringVar(value=str(self.data["settings"].get("work_minutes", 25)))
        break_var = tk.StringVar(value=str(self.data["settings"].get("break_minutes", 5)))

        body = tk.Frame(dialog, bg=colors["card_bg"], padx=16, pady=16)
        body.pack(fill="both", expand=True)

        tk.Label(body, text="主题", font=("Microsoft YaHei UI", 10, "bold"), bg=colors["card_bg"], fg=colors["text"]).grid(row=0, column=0, sticky="w")
        ttk.Combobox(body, textvariable=theme_var, values=list(THEMES.keys()), state="readonly", width=18).grid(row=0, column=1, sticky="ew", pady=(0, 10))

        tk.Label(body, text="工作时长（分钟）", font=("Microsoft YaHei UI", 10, "bold"), bg=colors["card_bg"], fg=colors["text"]).grid(row=1, column=0, sticky="w")
        ttk.Entry(body, textvariable=work_var, width=20).grid(row=1, column=1, sticky="ew", pady=(0, 10))

        tk.Label(body, text="休息时长（分钟）", font=("Microsoft YaHei UI", 10, "bold"), bg=colors["card_bg"], fg=colors["text"]).grid(row=2, column=0, sticky="w")
        ttk.Entry(body, textvariable=break_var, width=20).grid(row=2, column=1, sticky="ew", pady=(0, 14))

        button_row = tk.Frame(body, bg=colors["card_bg"])
        button_row.grid(row=3, column=0, columnspan=2, sticky="e")
        ttk.Button(button_row, text="保存", command=lambda: self.save_settings(dialog, theme_var.get(), work_var.get(), break_var.get()), style="Primary.TButton").pack(side="left")
        ttk.Button(button_row, text="取消", command=dialog.destroy).pack(side="left", padx=(8, 0))

        body.grid_columnconfigure(1, weight=1)

    def save_settings(self, dialog, theme_name, work_value, break_value):
        if theme_name not in THEMES:
            messagebox.showinfo("提示", "请选择支持的主题。", parent=dialog)
            return
        try:
            work_minutes = int(work_value)
            break_minutes = int(break_value)
        except ValueError:
            messagebox.showinfo("提示", "工作时长和休息时长必须是整数。", parent=dialog)
            return
        if work_minutes <= 0 or break_minutes <= 0:
            messagebox.showinfo("提示", "工作时长和休息时长必须大于 0。", parent=dialog)
            return

        self.data["settings"]["theme"] = theme_name
        self.data["settings"]["work_minutes"] = work_minutes
        self.data["settings"]["break_minutes"] = break_minutes
        self.timer.update_durations(work_minutes, break_minutes)
        self.storage.save(self.data)
        self._update_timer_display()
        self._apply_theme()
        self.refresh_task_list()
        self.refresh_slots()
        self.refresh_stats()
        self.refresh_history()
        dialog.destroy()

    def _apply_theme(self):
        colors = self._theme_colors()
        self.root.configure(bg=colors["app_bg"])
        self.style.configure("Card.TFrame", background=colors["card_bg"])
        self.style.configure("Section.TLabel", font=("Microsoft YaHei UI", 13, "bold"), background=colors["card_bg"], foreground=colors["text"])
        self.style.configure("Muted.TLabel", font=("Microsoft YaHei UI", 10), background=colors["card_bg"], foreground=colors["muted_text"])

        self.shell.configure(bg=colors["app_bg"])
        self.canvas.configure(bg=colors["app_bg"])
        self.content_frame.configure(bg=colors["app_bg"])
        self.header_card.configure(bg=colors["header_bg"])
        self.header_info_row.configure(bg=colors["header_bg"])
        self.header_title_label.configure(bg=colors["header_bg"], fg=colors["header_text"])
        self.date_label.configure(bg=colors["header_bg"], fg=colors["header_subtle"])
        self.header_spacer_label.configure(bg=colors["header_bg"], fg=colors["header_subtle"])
        self.time_label.configure(bg=colors["header_bg"], fg=colors["header_text"])

        for frame in [self.tasks_header_row, self.tasks_action_row, self.tasks_input_row, self.task_sections_frame, self.timer_button_row, self.slots_row, self.stats_grid, self.history_summary_row, self.history_frame]:
            frame.configure(bg=colors["card_bg"])
        self.timer_mode_label.configure(bg=colors["timer_badge_bg"], fg=colors["timer_badge_text"])
        self.timer_value_label.configure(bg=colors["card_bg"], fg=colors["text"])
        self.history_table_header.configure(bg=colors["section_bg"])
        for child in self.history_table_header.winfo_children():
            child.configure(bg=colors["section_bg"], fg=colors["secondary_text"])

        for card in [self.focus_tasks_card, self.break_tasks_card]:
            card["wrapper"].configure(bg=colors["section_bg"], highlightbackground=colors["border"])
            card["body"].configure(bg=colors["section_bg"])
            card["title"].configure(bg=colors["section_bg"], fg=colors["secondary_text"])

        self.refresh_slot_style()

    def add_task(self):
        title = self.task_title_var.get().strip()
        if not title:
            return

        task = {
            "id": str(uuid4()),
            "title": title,
            "task_type": self.task_type_var.get(),
            "completed": False,
            "created_at": datetime.now().isoformat(),
            "completed_at": None,
            "completion_count": 0,
            "last_completed_at": None,
        }
        self.data["tasks"].append(task)
        self.task_title_var.set("")
        self._save_and_refresh()

    def select_task(self, task_id):
        self.selected_task_id = task_id
        self.refresh_task_list()

    def assign_selected_task_to_focus(self):
        self._assign_selected_task("focus")

    def assign_selected_task_to_break(self):
        self._assign_selected_task("break")

    def _assign_selected_task(self, slot_type):
        if not self.selected_task_id:
            messagebox.showinfo("提示", "请先选择一个任务。")
            return

        task = self._find_task(self.selected_task_id)
        if not task:
            messagebox.showinfo("提示", "这个任务当前不能放入槽位。")
            return

        if task.get("task_type") != slot_type:
            target_name = "专注槽位" if slot_type == "focus" else "休息槽位"
            messagebox.showinfo("提示", f"这个任务类型不适合放入{target_name}。")
            return

        key = "focus_task_id" if slot_type == "focus" else "break_task_id"
        self.data["session_board"][key] = self.selected_task_id
        self._save_and_refresh()

    def complete_task_once(self, task_id):
        task = self._find_task(task_id)
        if not task:
            return

        completed_at = datetime.now().isoformat()
        task["completion_count"] = int(task.get("completion_count", 0)) + 1
        task["last_completed_at"] = completed_at
        task["completed"] = False
        task["completed_at"] = completed_at
        self.data["task_completion_events"].append(
            {
                "task_id": task_id,
                "task_type": task.get("task_type", "focus"),
                "completed_at": completed_at,
            }
        )
        self._save_and_refresh()

    def delete_task(self, task_id):
        self.data["tasks"] = [task for task in self.data["tasks"] if task["id"] != task_id]
        if self.selected_task_id == task_id:
            self.selected_task_id = None
        self._cleanup_slot_tasks_if_needed()
        self._save_and_refresh()

    def toggle_tasks_collapsed(self):
        self.tasks_collapsed = not self.tasks_collapsed
        self.refresh_task_list()

    def refresh_task_list(self):
        for frame in (self.focus_tasks_frame, self.break_tasks_frame):
            for child in list(frame.winfo_children()):
                child.destroy()

        self.tasks_toggle_button.configure(text="展开" if self.tasks_collapsed else "收起")

        tasks = self.data.get("tasks", [])
        focus_tasks = [task for task in tasks if task.get("task_type") == "focus"]
        break_tasks = [task for task in tasks if task.get("task_type") == "break"]

        if self.tasks_collapsed:
            focus_current = self._current_slot_task("focus_task_id")
            break_current = self._current_slot_task("break_task_id")
            if focus_current is None:
                self._render_task_placeholder(self.focus_tasks_frame, "当前未分配专注任务")
            else:
                self._render_task(self.focus_tasks_frame, focus_current)
            if break_current is None:
                self._render_task_placeholder(self.break_tasks_frame, "当前未分配休息任务")
            else:
                self._render_task(self.break_tasks_frame, break_current)
            return

        if not focus_tasks:
            self._render_task_placeholder(self.focus_tasks_frame, "还没有专注任务")
        else:
            for task in focus_tasks:
                self._render_task(self.focus_tasks_frame, task)

        if not break_tasks:
            self._render_task_placeholder(self.break_tasks_frame, "还没有休息任务")
        else:
            for task in break_tasks:
                self._render_task(self.break_tasks_frame, task)

    def _render_task_placeholder(self, parent, text):
        colors = self._theme_colors()
        tk.Label(parent, text=text, font=("Microsoft YaHei UI", 10), bg=colors["section_bg"], fg=colors["muted_text"], anchor="w").pack(anchor="w", pady=6)

    def _render_task(self, parent, task):
        colors = self._theme_colors()
        session_counts = task_session_counts(self.data).get(task["id"], {"work_sessions": 0, "break_sessions": 0})
        is_selected = task["id"] == self.selected_task_id
        is_focus_task = task["id"] == self.data["session_board"].get("focus_task_id")
        is_break_task = task["id"] == self.data["session_board"].get("break_task_id")
        row_bg = colors["selected_bg"] if is_selected else colors["card_bg"]
        row = tk.Frame(parent, bg=row_bg, padx=8, pady=8, highlightthickness=1, highlightbackground=colors["focus_active_border"] if is_selected else colors["border"])
        row.pack(fill="x", pady=4)
        row.bind("<Button-1>", lambda event, task_id=task["id"]: self.select_task(task_id))

        content = tk.Frame(row, bg=row_bg)
        content.pack(side="left", fill="x", expand=True)
        content.bind("<Button-1>", lambda event, task_id=task["id"]: self.select_task(task_id))

        label_prefix = "[休息] " if task.get("task_type") == "break" else "[专注] "
        tk.Label(content, text=f"{label_prefix}{task['title']}", font=("Microsoft YaHei UI", 11), bg=row_bg, fg=colors["text"], anchor="w").pack(anchor="w")

        status_parts = [f"完成 {int(task.get('completion_count', 0))} 次"]
        if session_counts["work_sessions"]:
            status_parts.append(f"专注 {session_counts['work_sessions']} 次")
        if session_counts["break_sessions"]:
            status_parts.append(f"休息 {session_counts['break_sessions']} 次")
        if task.get("last_completed_at"):
            status_parts.append(f"最近完成 {datetime.fromisoformat(task['last_completed_at']).strftime('%H:%M')}")
        tk.Label(content, text=" · ".join(status_parts), font=("Microsoft YaHei UI", 9), bg=row_bg, fg=colors["muted_text"], anchor="w", wraplength=200, justify="left").pack(anchor="w", pady=(4, 0))

        if is_focus_task:
            tk.Label(content, text="当前专注中", font=("Microsoft YaHei UI", 9), bg=row_bg, fg=colors["focus_active_text"], anchor="w").pack(anchor="w", pady=(2, 0))
        if is_break_task:
            tk.Label(content, text="当前休息任务", font=("Microsoft YaHei UI", 9), bg=row_bg, fg=colors["break_active_text"], anchor="w").pack(anchor="w", pady=(2, 0))

        actions = tk.Frame(row, bg=row_bg)
        actions.pack(side="right")
        ttk.Button(actions, text="完成一次", width=8, style="Primary.TButton", command=lambda task_id=task["id"]: self.complete_task_once(task_id)).pack(side="left")
        ttk.Button(actions, text="删除", width=6, style="Ghost.TButton", command=lambda task_id=task["id"]: self.delete_task(task_id)).pack(side="left", padx=(6, 0))

    def start_timer(self):
        focus_task = self._current_slot_task("focus_task_id")
        if self.timer.mode == "work" and focus_task is None:
            messagebox.showinfo("提示", "请先把一个专注任务放入当前专注槽位。")
            return
        self.timer.start()
        self._update_timer_display()
        self.refresh_slots()

    def pause_timer(self):
        self.timer.pause()
        self._update_timer_display()
        self.refresh_slots()

    def reset_timer(self):
        self.timer.reset()
        self._update_timer_display()
        self.refresh_slots()

    def switch_to_work(self):
        focus_task = self._current_slot_task("focus_task_id")
        self.timer.switch_to_work()
        self._update_timer_display()
        self.refresh_slots()
        if focus_task is None:
            messagebox.showinfo("提示", "当前没有专注任务，已切换到专注计时。")

    def switch_to_break(self):
        break_task = self._current_slot_task("break_task_id")
        self.timer.switch_to_break()
        self._update_timer_display()
        self.refresh_slots()
        if break_task is None:
            messagebox.showinfo("提示", "当前没有休息任务，已切换到休息计时。")

    def _schedule_tick(self):
        result = self.timer.tick()
        if result:
            task_key = "focus_task_id" if result["completed_mode"] == "work" else "break_task_id"
            self.data["focus_sessions"].append(
                {
                    "mode": result["completed_mode"],
                    "task_id": self.data["session_board"].get(task_key),
                    "started_at": result["started_at"].isoformat() if result["started_at"] else None,
                    "ended_at": result["ended_at"].isoformat(),
                    "duration_minutes": result["duration_minutes"],
                }
            )
            self.storage.save(self.data)
            self.refresh_stats()
            self.refresh_history()
            self.refresh_slots()
            self.refresh_task_list()
            if result["completed_mode"] == "work":
                self._show_windows_notification("专注完成", "本轮番茄专注已完成，开始休息吧。")
                messagebox.showinfo("专注完成", "本轮番茄专注已完成，开始休息吧。")
            else:
                self._show_windows_notification("休息结束", "休息时间结束，可以开始下一轮专注了。")
                messagebox.showinfo("休息结束", "休息时间结束，可以开始下一轮专注了。")

        self._update_timer_display()
        self.root.after(1000, self._schedule_tick)

    def _show_windows_notification(self, title, message):
        try:
            windll.user32.MessageBoxW(0, message, title, 0x40)
        except Exception:
            return

    def _update_timer_display(self):
        self.timer_text_var.set(self.timer.formatted_time())
        self.timer_mode_var.set(self.timer.mode_label())
        self.refresh_slot_style()

    def refresh_slots(self):
        focus_task = self._current_slot_task("focus_task_id")
        break_task = self._current_slot_task("break_task_id")

        if focus_task is None:
            self.focus_slot_title_var.set("暂未放入专注任务")
            self.focus_slot_hint_var.set("选择一个专注任务，然后点击“放入当前专注”。")
        else:
            self.focus_slot_title_var.set(focus_task["title"])
            self.focus_slot_hint_var.set("该任务将作为当前番茄专注目标。")

        if break_task is None:
            self.break_slot_title_var.set("暂未放入休息任务")
            if self.timer.mode == "break":
                self.break_slot_hint_var.set(f"当前在休息 {self.timer.formatted_time()}，可以先创建一个休息任务。")
            else:
                self.break_slot_hint_var.set("可以创建喝水、走动、拉伸等休息任务并放入这里。")
        else:
            self.break_slot_title_var.set(break_task["title"])
            if self.timer.mode == "break":
                self.break_slot_hint_var.set(f"现在适合做这个休息任务 · 剩余 {self.timer.formatted_time()}")
            else:
                self.break_slot_hint_var.set(f"下次休息时执行 · 休息时长 {self.timer.break_minutes} 分钟")

        self.refresh_slot_style()

    def refresh_slot_style(self):
        colors = self._theme_colors()
        focus_active = self.timer.mode == "work"
        break_active = self.timer.mode == "break"
        self.focus_slot_frame.configure(highlightbackground=colors["focus_active_border"] if focus_active else colors["slot_border"], bg=colors["focus_active_bg"] if focus_active else colors["section_bg"])
        self.break_slot_frame.configure(highlightbackground=colors["break_active_border"] if break_active else colors["slot_border"], bg=colors["break_active_bg"] if break_active else colors["section_bg"])
        for frame in [self.focus_slot_frame, self.break_slot_frame]:
            for child in frame.winfo_children():
                child.configure(bg=frame.cget("bg"), fg=colors["text"] if child.cget("font") != str(("Microsoft YaHei UI", 9)) else colors["muted_text"])

    def refresh_stats(self):
        summary = today_summary(self.data)
        totals = historical_summary(self.data)
        self.completed_tasks_var.set(f"{summary['completed_tasks']} 次")
        self.focus_minutes_var.set(f"{summary['focus_minutes']} 分钟")
        self.pomodoro_count_var.set(f"{summary['pomodoro_count']} 次")
        self.total_completed_tasks_var.set(f"{totals['total_completed_tasks']} 次")
        self.total_focus_minutes_var.set(f"{totals['total_focus_minutes']} 分钟")
        self.total_pomodoro_count_var.set(f"{totals['total_pomodoro_count']} 次")

    def refresh_history(self):
        colors = self._theme_colors()
        for child in self.history_frame.winfo_children():
            child.destroy()

        for item in recent_daily_records(self.data, days=7):
            row = tk.Frame(self.history_frame, bg=colors["card_bg"], padx=10, pady=8)
            row.pack(fill="x")
            tk.Label(row, text=item["label"], font=("Microsoft YaHei UI", 10), bg=colors["card_bg"], fg=colors["text"], width=8, anchor="w").grid(row=0, column=0, sticky="w")
            tk.Label(row, text=f"{item['completed_tasks']} 次", font=("Microsoft YaHei UI", 10), bg=colors["card_bg"], fg=colors["secondary_text"], width=10, anchor="w").grid(row=0, column=1, sticky="w", padx=(16, 0))
            tk.Label(row, text=f"{item['focus_minutes']} 分钟", font=("Microsoft YaHei UI", 10), bg=colors["card_bg"], fg=colors["secondary_text"], width=12, anchor="w").grid(row=0, column=2, sticky="w", padx=(16, 0))

    def _rollover_day_if_needed(self):
        today = date.today().isoformat()
        last_active_date = self.data.get("last_active_date", today)
        if last_active_date == today:
            return

        previous_day = datetime.fromisoformat(last_active_date).date()
        current_day = date.today()

        while previous_day < current_day:
            day_key = previous_day.isoformat()
            self.data["daily_records"][day_key] = build_daily_record(self.data, previous_day)
            previous_day += timedelta(days=1)

        self._cleanup_slot_tasks_if_needed()
        self.data["last_active_date"] = today
        self.storage.save(self.data)

    def _save_and_refresh(self):
        self.data["last_active_date"] = date.today().isoformat()
        self._cleanup_slot_tasks_if_needed()
        self.storage.save(self.data)
        self.refresh_task_list()
        self.refresh_slots()
        self.refresh_stats()
        self.refresh_history()

    def _update_clock(self):
        now = datetime.now()
        self.date_text_var.set(now.strftime("%Y-%m-%d %A"))
        self.time_text_var.set(now.strftime("%H:%M:%S"))
        self.root.after(1000, self._update_clock)

    def _find_task(self, task_id):
        for task in self.data["tasks"]:
            if task["id"] == task_id:
                return task
        return None

    def _current_slot_task(self, key):
        task_id = self.data["session_board"].get(key)
        if not task_id:
            return None
        return self._find_task(task_id)

    def _cleanup_slot_tasks_if_needed(self):
        if self._current_slot_task("focus_task_id") is None:
            self.data["session_board"]["focus_task_id"] = None
        if self._current_slot_task("break_task_id") is None:
            self.data["session_board"]["break_task_id"] = None

    def _ensure_task_defaults(self):
        migrated_events = list(self.data.get("task_completion_events", []))
        self.data.setdefault("settings", {})
        self.data["settings"].setdefault("theme", "light")
        for task in self.data.get("tasks", []):
            task.setdefault("task_type", "focus")
            task.setdefault("completion_count", 0)
            task.setdefault("last_completed_at", None)
            if task.get("completed") and task.get("completed_at"):
                task["completion_count"] = max(int(task.get("completion_count", 0)), 1)
                task["last_completed_at"] = task.get("completed_at")
                if not any(event.get("task_id") == task["id"] and event.get("completed_at") == task.get("completed_at") for event in migrated_events):
                    migrated_events.append(
                        {
                            "task_id": task["id"],
                            "task_type": task.get("task_type", "focus"),
                            "completed_at": task.get("completed_at"),
                        }
                    )
                task["completed"] = False
        self.data["task_completion_events"] = migrated_events
        self.data["session_board"].setdefault("focus_task_id", None)
        self.data["session_board"].setdefault("break_task_id", None)
        for session in self.data.get("focus_sessions", []):
            session.setdefault("task_id", None)

    def _on_content_configure(self, event):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _on_canvas_configure(self, event):
        self.canvas.itemconfigure(self.canvas_window, width=event.width)

    def _bind_mousewheel(self):
        self.root.bind_all("<MouseWheel>", self._on_mousewheel)

    def _on_mousewheel(self, event):
        self.canvas.yview_scroll(int(-event.delta / 120), "units")

    def run(self):
        self.root.mainloop()
