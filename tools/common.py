from __future__ import annotations

from pathlib import Path

ENCODINGS = ("utf-8-sig", "utf-8", "gb18030", "big5", "cp1252")


def read_text_any(path: Path) -> tuple[str, str]:
    last_error: Exception | None = None
    for encoding in ENCODINGS:
        try:
            return path.read_text(encoding=encoding), encoding
        except UnicodeDecodeError as exc:
            last_error = exc
    return path.read_text(encoding="utf-8", errors="replace"), "utf-8-replace"


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
