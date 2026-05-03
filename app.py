import tkinter as tk
from datetime import date, datetime, timedelta
from tkinter import messagebox, ttk
from uuid import uuid4

from pomodoro import PomodoroTimer
from stats import build_daily_record, historical_summary, recent_daily_records, task_session_counts, today_summary
from storage import Storage


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
        self.root.configure(bg="#eef2ff")

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

        self._build_ui()
        self._bind_mousewheel()
        self._update_clock()
        self.refresh_task_list()
        self.refresh_slots()
        self.refresh_stats()
        self.refresh_history()
        self._schedule_tick()

    def _build_ui(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Card.TFrame", background="#ffffff")
        style.configure("Section.TLabel", font=("Microsoft YaHei UI", 13, "bold"), background="#ffffff", foreground="#111827")
        style.configure("Muted.TLabel", font=("Microsoft YaHei UI", 10), background="#ffffff", foreground="#6b7280")
        style.configure("Primary.TButton", font=("Microsoft YaHei UI", 10, "bold"))
        style.configure("Ghost.TButton", font=("Microsoft YaHei UI", 9))

        shell = tk.Frame(self.root, bg="#eef2ff")
        shell.pack(fill="both", expand=True)

        self.canvas = tk.Canvas(shell, bg="#eef2ff", highlightthickness=0)
        self.canvas.pack(side="left", fill="both", expand=True)

        scrollbar = ttk.Scrollbar(shell, orient="vertical", command=self.canvas.yview)
        scrollbar.pack(side="right", fill="y")
        self.canvas.configure(yscrollcommand=scrollbar.set)

        self.content_frame = tk.Frame(self.canvas, bg="#eef2ff", padx=16, pady=16)
        self.canvas_window = self.canvas.create_window((0, 0), window=self.content_frame, anchor="nw")
        self.content_frame.bind("<Configure>", self._on_content_configure)
        self.canvas.bind("<Configure>", self._on_canvas_configure)

        self._build_header(self.content_frame)
        self._build_tasks_card(self.content_frame)
        self._build_timer_card(self.content_frame)
        self._build_stats_card(self.content_frame)
        self._build_history_card(self.content_frame)

    def _build_header(self, parent):
        card = tk.Frame(parent, bg="#4f46e5", padx=18, pady=18)
        card.pack(fill="x", pady=(0, 12))

        tk.Label(
            card,
            text="每日任务小展板",
            font=("Microsoft YaHei UI", 18, "bold"),
            bg="#4f46e5",
            fg="#ffffff",
        ).pack(anchor="w")

        info_row = tk.Frame(card, bg="#4f46e5")
        info_row.pack(anchor="w", pady=(6, 0))
        tk.Label(info_row, textvariable=self.date_text_var, font=("Microsoft YaHei UI", 10), bg="#4f46e5", fg="#dbeafe").pack(side="left")
        tk.Label(info_row, text="  ", font=("Microsoft YaHei UI", 10), bg="#4f46e5", fg="#dbeafe").pack(side="left")
        tk.Label(info_row, textvariable=self.time_text_var, font=("Consolas", 11, "bold"), bg="#4f46e5", fg="#ffffff").pack(side="left")

    def _build_tasks_card(self, parent):
        card = ttk.Frame(parent, style="Card.TFrame", padding=16)
        card.pack(fill="x", pady=(0, 12))

        header_row = tk.Frame(card, bg="#ffffff")
        header_row.pack(fill="x")
        ttk.Label(header_row, text="任务列表", style="Section.TLabel").pack(side="left")

        action_row = tk.Frame(card, bg="#ffffff")
        action_row.pack(fill="x", pady=(10, 0))
        ttk.Button(action_row, text="放入当前专注", command=self.assign_selected_task_to_focus, style="Primary.TButton").pack(side="left")
        ttk.Button(action_row, text="放入休息槽位", command=self.assign_selected_task_to_break, style="Primary.TButton").pack(side="left", padx=(8, 0))

        input_row = tk.Frame(card, bg="#ffffff")
        input_row.pack(fill="x", pady=(12, 10))

        entry = ttk.Entry(input_row, textvariable=self.task_title_var, font=("Microsoft YaHei UI", 11))
        entry.pack(side="left", fill="x", expand=True)
        entry.bind("<Return>", lambda event: self.add_task())

        task_type_box = ttk.Combobox(input_row, textvariable=self.task_type_var, values=["focus", "break"], state="readonly", width=8)
        task_type_box.pack(side="left", padx=(8, 0))

        ttk.Button(input_row, text="添加", command=self.add_task, style="Primary.TButton").pack(side="left", padx=(8, 0))

        ttk.Label(card, text="点击任务可选中，再放入专注槽位或休息槽位。", style="Muted.TLabel").pack(anchor="w", pady=(0, 8))
        self.pending_tasks_frame = tk.Frame(card, bg="#ffffff")
        self.pending_tasks_frame.pack(fill="x")

    def _build_timer_card(self, parent):
        card = ttk.Frame(parent, style="Card.TFrame", padding=16)
        card.pack(fill="x", pady=(0, 12))

        ttk.Label(card, text="番茄专注", style="Section.TLabel").pack(anchor="w")

        tk.Label(card, textvariable=self.timer_mode_var, font=("Microsoft YaHei UI", 10, "bold"), bg="#eef2ff", fg="#4338ca", padx=12, pady=6).pack(anchor="w", pady=(10, 8))

        slots_row = tk.Frame(card, bg="#ffffff")
        slots_row.pack(fill="x", pady=(0, 12))

        self.focus_slot_frame = self._build_slot_card(slots_row, "当前专注槽位", self.focus_slot_title_var, self.focus_slot_hint_var)
        self.focus_slot_frame.pack(side="left", expand=True, fill="both")
        self._bind_slot_click(self.focus_slot_frame, self.switch_to_work)
        self.break_slot_frame = self._build_slot_card(slots_row, "休息槽位", self.break_slot_title_var, self.break_slot_hint_var)
        self.break_slot_frame.pack(side="left", expand=True, fill="both", padx=(10, 0))
        self._bind_slot_click(self.break_slot_frame, self.switch_to_break)

        tk.Label(card, textvariable=self.timer_text_var, font=("Consolas", 34, "bold"), bg="#ffffff", fg="#111827").pack(anchor="center", pady=(2, 12))

        button_row = tk.Frame(card, bg="#ffffff")
        button_row.pack(fill="x")

        ttk.Button(button_row, text="开始", command=self.start_timer, style="Primary.TButton").pack(side="left", expand=True, fill="x")
        ttk.Button(button_row, text="暂停", command=self.pause_timer).pack(side="left", expand=True, fill="x", padx=8)
        ttk.Button(button_row, text="重置", command=self.reset_timer).pack(side="left", expand=True, fill="x")

    def _build_slot_card(self, parent, title, primary_var, secondary_var):
        frame = tk.Frame(parent, bg="#f8fafc", padx=12, pady=12, highlightthickness=2, highlightbackground="#e2e8f0")
        tk.Label(frame, text=title, font=("Microsoft YaHei UI", 10, "bold"), bg="#f8fafc", fg="#334155").pack(anchor="w")
        tk.Label(frame, textvariable=primary_var, font=("Microsoft YaHei UI", 11, "bold"), bg="#f8fafc", fg="#111827", wraplength=180, justify="left").pack(anchor="w", pady=(10, 4))
        tk.Label(frame, textvariable=secondary_var, font=("Microsoft YaHei UI", 9), bg="#f8fafc", fg="#64748b", wraplength=180, justify="left").pack(anchor="w")
        return frame

    def _build_stats_card(self, parent):
        card = ttk.Frame(parent, style="Card.TFrame", padding=16)
        card.pack(fill="x", pady=(0, 12))

        ttk.Label(card, text="今日统计", style="Section.TLabel").pack(anchor="w")

        grid = tk.Frame(card, bg="#ffffff")
        grid.pack(fill="x", pady=(12, 0))

        self._build_stat_tile(grid, "完成次数", self.completed_tasks_var, 0, 0)
        self._build_stat_tile(grid, "专注时长", self.focus_minutes_var, 0, 1)
        self._build_stat_tile(grid, "完成番茄", self.pomodoro_count_var, 1, 0)
        self._build_stat_tile(grid, "累计完成", self.total_completed_tasks_var, 1, 1)

    def _build_history_card(self, parent):
        card = ttk.Frame(parent, style="Card.TFrame", padding=16)
        card.pack(fill="both", expand=True)

        ttk.Label(card, text="历史统计", style="Section.TLabel").pack(anchor="w")

        summary_row = tk.Frame(card, bg="#ffffff")
        summary_row.pack(fill="x", pady=(12, 12))

        self._build_history_summary_item(summary_row, "累计专注", self.total_focus_minutes_var).pack(side="left", expand=True, fill="x")
        self._build_history_summary_item(summary_row, "累计番茄", self.total_pomodoro_count_var).pack(side="left", expand=True, fill="x", padx=8)

        table_header = tk.Frame(card, bg="#f8fafc", padx=10, pady=8)
        table_header.pack(fill="x")
        tk.Label(table_header, text="日期", font=("Microsoft YaHei UI", 9, "bold"), bg="#f8fafc", fg="#475569").grid(row=0, column=0, sticky="w")
        tk.Label(table_header, text="完成", font=("Microsoft YaHei UI", 9, "bold"), bg="#f8fafc", fg="#475569").grid(row=0, column=1, sticky="w", padx=(24, 0))
        tk.Label(table_header, text="专注", font=("Microsoft YaHei UI", 9, "bold"), bg="#f8fafc", fg="#475569").grid(row=0, column=2, sticky="w", padx=(24, 0))

        self.history_frame = tk.Frame(card, bg="#ffffff")
        self.history_frame.pack(fill="both", expand=True, pady=(8, 0))

    def _bind_slot_click(self, frame, callback):
        frame.bind("<Button-1>", lambda event: callback())
        for child in frame.winfo_children():
            child.bind("<Button-1>", lambda event: callback())

    def _build_stat_tile(self, parent, label, variable, row, column):
        tile = tk.Frame(parent, bg="#f8fafc", padx=12, pady=12)
        tile.grid(row=row, column=column, sticky="nsew", padx=4, pady=4)
        parent.grid_columnconfigure(column, weight=1)
        tk.Label(tile, text=label, font=("Microsoft YaHei UI", 10), bg="#f8fafc", fg="#475569").pack(anchor="w")
        tk.Label(tile, textvariable=variable, font=("Microsoft YaHei UI", 14, "bold"), bg="#f8fafc", fg="#111827").pack(anchor="w", pady=(6, 0))

    def _build_history_summary_item(self, parent, label, variable):
        frame = tk.Frame(parent, bg="#f8fafc", padx=12, pady=12)
        tk.Label(frame, text=label, font=("Microsoft YaHei UI", 10), bg="#f8fafc", fg="#475569").pack(anchor="w")
        tk.Label(frame, textvariable=variable, font=("Microsoft YaHei UI", 13, "bold"), bg="#f8fafc", fg="#111827").pack(anchor="w", pady=(4, 0))
        return frame

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

    def refresh_task_list(self):
        for frame in list(self.pending_tasks_frame.winfo_children()):
            frame.destroy()

        tasks = self.data.get("tasks", [])
        if not tasks:
            ttk.Label(self.pending_tasks_frame, text="还没有任务，先加一个吧。", style="Muted.TLabel").pack(anchor="w", pady=4)
            return

        for task in tasks:
            self._render_task(self.pending_tasks_frame, task)

    def _render_task(self, parent, task):
        session_counts = task_session_counts(self.data).get(task["id"], {"work_sessions": 0, "break_sessions": 0})
        is_selected = task["id"] == self.selected_task_id
        is_focus_task = task["id"] == self.data["session_board"].get("focus_task_id")
        is_break_task = task["id"] == self.data["session_board"].get("break_task_id")
        row_bg = "#ede9fe" if is_selected else "#ffffff"
        row = tk.Frame(parent, bg=row_bg, padx=8, pady=8, highlightthickness=1, highlightbackground="#c4b5fd" if is_selected else "#e5e7eb")
        row.pack(fill="x", pady=4)
        row.bind("<Button-1>", lambda event, task_id=task["id"]: self.select_task(task_id))

        content = tk.Frame(row, bg=row_bg)
        content.pack(side="left", fill="x", expand=True)
        content.bind("<Button-1>", lambda event, task_id=task["id"]: self.select_task(task_id))

        label_prefix = "[休息] " if task.get("task_type") == "break" else "[专注] "
        tk.Label(content, text=f"{label_prefix}{task['title']}", font=("Microsoft YaHei UI", 11), bg=row_bg, fg="#111827", anchor="w").pack(anchor="w")

        status_parts = [f"完成 {int(task.get('completion_count', 0))} 次"]
        if session_counts["work_sessions"]:
            status_parts.append(f"专注 {session_counts['work_sessions']} 次")
        if session_counts["break_sessions"]:
            status_parts.append(f"休息 {session_counts['break_sessions']} 次")
        if task.get("last_completed_at"):
            status_parts.append(f"最近完成 {datetime.fromisoformat(task['last_completed_at']).strftime('%H:%M')}")
        tk.Label(content, text=" · ".join(status_parts), font=("Microsoft YaHei UI", 9), bg=row_bg, fg="#64748b", anchor="w").pack(anchor="w", pady=(4, 0))

        if is_focus_task:
            tk.Label(content, text="当前专注中", font=("Microsoft YaHei UI", 9), bg=row_bg, fg="#7c3aed", anchor="w").pack(anchor="w", pady=(2, 0))
        if is_break_task:
            tk.Label(content, text="当前休息任务", font=("Microsoft YaHei UI", 9), bg=row_bg, fg="#0284c7", anchor="w").pack(anchor="w", pady=(2, 0))

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
                messagebox.showinfo("专注完成", "本轮番茄专注已完成，开始休息吧。")
            else:
                messagebox.showinfo("休息结束", "休息时间结束，可以开始下一轮专注了。")

        self._update_timer_display()
        self.root.after(1000, self._schedule_tick)

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
        focus_active = self.timer.mode == "work"
        break_active = self.timer.mode == "break"
        self.focus_slot_frame.configure(highlightbackground="#7c3aed" if focus_active else "#e2e8f0", bg="#f5f3ff" if focus_active else "#f8fafc")
        self.break_slot_frame.configure(highlightbackground="#0ea5e9" if break_active else "#e2e8f0", bg="#eff6ff" if break_active else "#f8fafc")

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
        for child in self.history_frame.winfo_children():
            child.destroy()

        for item in recent_daily_records(self.data, days=7):
            row = tk.Frame(self.history_frame, bg="#ffffff", padx=10, pady=8)
            row.pack(fill="x")
            tk.Label(row, text=item["label"], font=("Microsoft YaHei UI", 10), bg="#ffffff", fg="#111827", width=8, anchor="w").grid(row=0, column=0, sticky="w")
            tk.Label(row, text=f"{item['completed_tasks']} 次", font=("Microsoft YaHei UI", 10), bg="#ffffff", fg="#334155", width=10, anchor="w").grid(row=0, column=1, sticky="w", padx=(16, 0))
            tk.Label(row, text=f"{item['focus_minutes']} 分钟", font=("Microsoft YaHei UI", 10), bg="#ffffff", fg="#334155", width=12, anchor="w").grid(row=0, column=2, sticky="w", padx=(16, 0))

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
