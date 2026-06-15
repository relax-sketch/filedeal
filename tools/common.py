from __future__ import annotations

from core.path_utils import ensure_dir, system_path
from pathlib import Path

ENCODINGS = ("utf-8-sig", "utf-8", "gb18030", "big5", "cp1252")


def read_text_any(path: Path) -> tuple[str, str]:
    last_error: Exception | None = None
    for encoding in ENCODINGS:
        try:
            with open(system_path(path), "r", encoding=encoding) as fh:
                return fh.read(), encoding
        except UnicodeDecodeError as exc:
            last_error = exc
    with open(system_path(path), "r", encoding="utf-8", errors="replace") as fh:
        return fh.read(), "utf-8-replace"


def write_text_file(path: Path, text: str, encoding: str = "utf-8", newline: str | None = None) -> None:
    ensure_dir(path.parent)
    with open(system_path(path), "w", encoding=encoding, newline=newline) as fh:
        fh.write(text)


def iter_files(root: Path, recursive: bool = False, suffixes: tuple[str, ...] = ()) -> list[Path]:
    pattern = "**/*" if recursive else "*"
    files = [path for path in root.glob(pattern) if path.is_file()]
    if suffixes:
        lowered = tuple(s.lower() for s in suffixes)
        files = [path for path in files if path.suffix.lower() in lowered]
    return sorted(files)


def result(success: bool = True, message: str = "", output: str = "", stats=None, **extra):
    data = {
        "success": success,
        "message": message,
        "output": output,
        "stats": stats or {},
    }
    data.update(extra)
    return data
