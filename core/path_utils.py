from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path

from config import APP_DIR

TASKS_DIR = APP_DIR / "records" / "tasks"
WINDOWS_PATH_SOFT_LIMIT = 240


def ensure_base_dirs() -> None:
    TASKS_DIR.mkdir(parents=True, exist_ok=True)
    (APP_DIR / "records" / "logs").mkdir(parents=True, exist_ok=True)


def normalize_path(value: str | Path | None) -> Path | None:
    if value in (None, ""):
        return None
    return Path(str(value)).expanduser().resolve()


def system_path(path: str | Path) -> str:
    value = str(path)
    if os.name != "nt":
        return value
    if value.startswith("\\\\?\\"):
        return value
    if value.startswith("\\\\"):
        return "\\\\?\\UNC\\" + value[2:]
    return "\\\\?\\" + value


def ensure_dir(path: Path) -> None:
    os.makedirs(system_path(path), exist_ok=True)


def path_exists(path: Path) -> bool:
    return os.path.exists(system_path(path))


def fit_path_length(path: Path, max_length: int = WINDOWS_PATH_SOFT_LIMIT) -> Path:
    raw = str(path)
    if os.name != "nt" or len(raw) <= max_length:
        return path

    parent = path.parent
    suffix = path.suffix
    name = path.name
    stem = path.stem if suffix else name
    ext = suffix if suffix else ""

    overflow = len(raw) - max_length
    target_stem_length = max(8, len(stem) - overflow)
    if len(stem) <= target_stem_length:
        return path

    while target_stem_length >= 8:
        if target_stem_length <= 16:
            shortened = stem[:target_stem_length]
        else:
            head = min(40, max(8, target_stem_length // 2))
            tail = max(8, target_stem_length - head - 1)
            shortened = f"{stem[:head]}_{stem[-tail:]}"
            if len(shortened) > target_stem_length:
                shortened = shortened[:target_stem_length]
        candidate = parent / f"{shortened}{ext}"
        if len(str(candidate)) <= max_length:
            return candidate
        target_stem_length -= 1

    return parent / f"{stem[:8]}{ext}"


def make_task_id() -> str:
    return "task_" + datetime.now().strftime("%Y%m%d_%H%M%S_%f")


def task_dir(task_id: str) -> Path:
    safe_id = "".join(ch for ch in task_id if ch.isalnum() or ch in {"_", "-"})
    path = (TASKS_DIR / safe_id).resolve()
    if TASKS_DIR.resolve() not in path.parents and path != TASKS_DIR.resolve():
        raise ValueError("Invalid task id")
    return path


def unique_path(path: Path) -> Path:
    candidate = fit_path_length(path)
    if not path_exists(candidate):
        return candidate
    stem = candidate.stem
    suffix = candidate.suffix
    parent = candidate.parent
    idx = 1
    while True:
        candidate = fit_path_length(parent / f"{stem}_{idx}{suffix}")
        if not path_exists(candidate):
            return candidate
        idx += 1
