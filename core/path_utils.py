from __future__ import annotations

from datetime import datetime
from pathlib import Path

from config import APP_DIR

TASKS_DIR = APP_DIR / "records" / "tasks"


def ensure_base_dirs() -> None:
    TASKS_DIR.mkdir(parents=True, exist_ok=True)
    (APP_DIR / "records" / "logs").mkdir(parents=True, exist_ok=True)


def normalize_path(value: str | Path | None) -> Path | None:
    if value in (None, ""):
        return None
    return Path(str(value)).expanduser().resolve()


def make_task_id() -> str:
    return "task_" + datetime.now().strftime("%Y%m%d_%H%M%S_%f")


def task_dir(task_id: str) -> Path:
    safe_id = "".join(ch for ch in task_id if ch.isalnum() or ch in {"_", "-"})
    path = (TASKS_DIR / safe_id).resolve()
    if TASKS_DIR.resolve() not in path.parents and path != TASKS_DIR.resolve():
        raise ValueError("Invalid task id")
    return path


def unique_path(path: Path) -> Path:
    if not path.exists():
        return path
    stem = path.stem
    suffix = path.suffix
    parent = path.parent
    idx = 1
    while True:
        candidate = parent / f"{stem}_{idx}{suffix}"
        if not candidate.exists():
            return candidate
        idx += 1
