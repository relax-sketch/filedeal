from __future__ import annotations

import json
from pathlib import Path
from typing import Any

APP_DIR = Path(__file__).resolve().parent
CONFIG_PATH = APP_DIR / "config.json"

DEFAULT_SETTINGS: dict[str, Any] = {
    "default_input_dir": "",
    "default_output_dir": "",
    "log_dir": str(APP_DIR / "records" / "tasks"),
    "recursive_default": False,
    "delete_strategy": "_trash",
    "max_concurrency": 2,
    "dangerous_confirm": True,
    "preview_default": True,
    "allow_overwrite": False,
    "save_logs": True,
}


def load_settings() -> dict[str, Any]:
    if not CONFIG_PATH.exists():
        return DEFAULT_SETTINGS.copy()
    try:
        data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return DEFAULT_SETTINGS.copy()
    settings = DEFAULT_SETTINGS.copy()
    settings.update({k: v for k, v in data.items() if k in DEFAULT_SETTINGS})
    return settings


def save_settings(settings: dict[str, Any]) -> dict[str, Any]:
    merged = DEFAULT_SETTINGS.copy()
    merged.update({k: v for k, v in settings.items() if k in DEFAULT_SETTINGS})
    merged["max_concurrency"] = max(1, int(merged.get("max_concurrency") or 1))
    CONFIG_PATH.write_text(
        json.dumps(merged, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return merged
