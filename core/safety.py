from __future__ import annotations

import shutil
from pathlib import Path

from core.path_utils import unique_path


def delete_or_trash(path: Path, settings: dict, logger, preview: bool = False) -> bool:
    path = path.resolve()
    strategy = settings.get("delete_strategy", "_trash")
    if preview:
        logger.info("Preview delete", path=str(path), strategy=strategy)
        return True
    if not path.exists():
        logger.warning("Delete target missing", path=str(path))
        return False
    if strategy == "_trash":
        trash_dir = path.parent / "_trash"
        trash_dir.mkdir(parents=True, exist_ok=True)
        target = unique_path(trash_dir / path.name)
        shutil.move(str(path), str(target))
        logger.info("Moved to _trash", source=str(path), target=str(target))
        return True
    if path.is_dir():
        shutil.rmtree(path)
    else:
        path.unlink()
    logger.info("Deleted", path=str(path))
    return True
