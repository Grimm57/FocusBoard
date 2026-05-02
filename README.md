# FocusBoard

A clean and lightweight desktop task board for daily planning, Pomodoro focus, and personal progress tracking.

## Why FocusBoard

FocusBoard is built for people who want a small desktop app that stays simple:
- plan today’s tasks quickly
- switch between focus and break modes naturally
- track completed tasks and focus time
- keep everything local with no account required

## Features

- Daily task board with focus tasks and break tasks
- Pomodoro timer with focus mode and break mode
- Clickable focus slot and break slot to switch modes
- Task assignment to current focus slot and break slot
- Daily statistics for completed tasks, focus minutes, and finished Pomodoros
- Historical records with recent-day summaries
- Automatic daily rollover
- Local JSON data storage
- Scrollable compact desktop UI for Windows

## Screens at a glance

- **Task area**: create tasks, tag them as focus or break, and assign them to slots
- **Pomodoro area**: start, pause, reset, and switch modes by clicking the slots
- **Stats area**: view today’s progress and historical totals

## Tech Stack

- Python
- Tkinter
- JSON local storage

## Project Structure

```text
main.py        # app entry point
app.py         # UI and app workflow
pomodoro.py    # pomodoro timer state machine
storage.py     # local persistence
stats.py       # statistics aggregation
data/          # local runtime data
```

## Run Locally

```bash
python main.py
```

## Privacy

All personal task and focus data is stored locally in `data/data.json`.
The repository includes a `.gitignore` rule so this file is not uploaded by default.

## Open Source License

This project is licensed under the MIT License.

## Suggested GitHub title and description

**Repository title**
- FocusBoard

**Short description**
- A lightweight desktop task board with Pomodoro focus, break slots, and local progress tracking.

**Alternative description**
- Plan your day, focus with Pomodoro, switch between work and break slots, and keep your progress private on your own desktop.
