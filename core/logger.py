from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any


class TaskLogger:
    def __init__(self, log_path: Path):
        self.log_path = log_path
        self.log_path.parent.mkdir(parents=True, exist_ok=True)

    def write(self, level: str, message: str, **data: Any) -> None:
        stamp = datetime.now().isoformat(timespec="seconds")
        extra = ""
        if data:
            parts = [f"{key}={value}" for key, value in data.items()]
            extra = " | " + " ".join(parts)
        with self.log_path.open("a", encoding="utf-8", newline="\n") as fh:
            fh.write(f"[{stamp}] [{level.upper()}] {message}{extra}\n")

    def info(self, message: str, **data: Any) -> None:
        self.write("info", message, **data)

    def success(self, message: str, **data: Any) -> None:
        self.write("success", message, **data)

    def warning(self, message: str, **data: Any) -> None:
        self.write("warning", message, **data)

    def error(self, message: str, **data: Any) -> None:
        self.write("error", message, **data)
