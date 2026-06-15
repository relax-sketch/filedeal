from __future__ import annotations

import sys
from pathlib import Path

import uvicorn


def main() -> None:
    project_root = Path(__file__).resolve().parent.parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))
    uvicorn.run("app.main:app", host="127.0.0.1", port=8005)


if __name__ == "__main__":
    main()
