from __future__ import annotations

import shutil
from pathlib import Path

from core.path_utils import normalize_path, unique_path
from core.safety import delete_or_trash
from tools.common import iter_files, result


def group_files(params: dict, context: dict) -> dict:
    input_dir = normalize_path(params.get("input_dir"))
    if not input_dir or not input_dir.is_dir():
        raise ValueError("input_dir is required")
    per_group = max(1, int(params.get("files_per_group") or 80))
    preview = context.get("preview", False)
    logger = context["logger"]
    files = [path for path in iter_files(input_dir) if not path.name.startswith("task_")]
    stats = {"files": len(files), "groups": 0, "moved": 0}
    for idx, src in enumerate(files):
        context["check_cancel"]()
        group_no = idx // per_group + 1
        group_dir = input_dir / f"group_{group_no}"
        dst = group_dir / src.name
        stats["groups"] = max(stats["groups"], group_no)
        if preview:
            logger.info("Preview group move", source=str(src), target=str(dst))
        else:
            group_dir.mkdir(parents=True, exist_ok=True)
            shutil.move(str(src), str(unique_path(dst)))
            logger.info("Moved file to group", source=str(src), target=str(dst))
            stats["moved"] += 1
    return result(True, "文件夹分组完成", str(input_dir), stats)


def split_large_folder(params: dict, context: dict) -> dict:
    return group_files(params, context)


def filter_files_by_size(params: dict, context: dict) -> dict:
    input_dir = normalize_path(params.get("input_dir"))
    if not input_dir or not input_dir.is_dir():
        raise ValueError("input_dir is required")
    output_dir = normalize_path(params.get("output_dir")) or input_dir / "size_filtered"
    min_size = float(params.get("min_size_mb") or 0) * 1024 * 1024
    preview = context.get("preview", False)
    logger = context["logger"]
    stats = {"matched": 0}
    for src in iter_files(input_dir):
        context["check_cancel"]()
        if output_dir in src.parents:
            continue
        if src.stat().st_size >= min_size:
            dst = output_dir / src.name
            stats["matched"] += 1
            if preview:
                logger.info("Preview size filter copy", source=str(src), target=str(dst))
            else:
                output_dir.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, unique_path(dst))
    return result(True, "文件大小筛选完成", str(output_dir), stats)


def batch_change_extension(params: dict, context: dict) -> dict:
    input_dir = normalize_path(params.get("input_dir"))
    if not input_dir or not input_dir.is_dir():
        raise ValueError("input_dir is required")
    extension = str(params.get("extension") or ".rar")
    if not extension.startswith("."):
        extension = "." + extension
    preview = context.get("preview", False)
    logger = context["logger"]
    stats = {"renamed": 0}
    for src in iter_files(input_dir):
        context["check_cancel"]()
        dst = src.with_suffix(extension)
        if preview:
            logger.info("Preview extension change", source=str(src), target=str(dst))
        else:
            src.rename(unique_path(dst))
            logger.info("Extension changed", source=str(src), target=str(dst))
            stats["renamed"] += 1
    return result(True, "批量后缀修改完成", str(input_dir), stats)


def delete_empty_folders(params: dict, context: dict) -> dict:
    input_dir = normalize_path(params.get("input_dir"))
    if not input_dir or not input_dir.is_dir():
        raise ValueError("input_dir is required")
    enabled = bool(params.get("enable_delete"))
    preview = context.get("preview", False)
    logger = context["logger"]
    stats = {"empty": 0, "deleted": 0, "skipped": 0}
    dirs = sorted([p for p in input_dir.rglob("*") if p.is_dir()], key=lambda p: len(p.parts), reverse=True)
    for folder in dirs:
        context["check_cancel"]()
        if any(folder.iterdir()):
            continue
        stats["empty"] += 1
        if enabled:
            if delete_or_trash(folder, context["settings"], logger, preview=preview):
                stats["deleted"] += 1
        else:
            logger.info("Empty folder delete skipped", path=str(folder))
            stats["skipped"] += 1
    return result(True, "空文件夹清理完成", str(input_dir), stats)
