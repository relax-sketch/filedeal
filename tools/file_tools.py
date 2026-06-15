from __future__ import annotations

import os
import shutil
from string import ascii_lowercase, ascii_uppercase
from pathlib import Path

from core.path_utils import ensure_dir, fit_path_length, normalize_path, path_exists, system_path, unique_path
from core.safety import delete_or_trash
from tools.common import iter_files, result


FOLDER_SIZE_PREFIXES = tuple(ascii_uppercase + ascii_lowercase)


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
            ensure_dir(group_dir)
            shutil.move(system_path(src), system_path(unique_path(fit_path_length(dst))))
            logger.info("Moved file to group", source=str(src), target=str(dst))
            stats["moved"] += 1
    return result(True, "文件夹分组完成", str(input_dir), stats)


def split_large_folder(params: dict, context: dict) -> dict:
    return group_files(params, context)


def folder_size_bytes(folder: Path) -> int:
    total = 0
    for path in folder.rglob("*"):
        if path.is_file():
            total += path.stat().st_size
    return total


def has_size_rank_prefix(folder_name: str) -> bool:
    return len(folder_name) > 2 and folder_name[1] == "_" and folder_name[0] in FOLDER_SIZE_PREFIXES


def sort_folders_by_size_rename(params: dict, context: dict) -> dict:
    input_dir = normalize_path(params.get("input_dir"))
    if not input_dir or not input_dir.is_dir():
        raise ValueError("input_dir is required")
    restore_prefixes = bool(params.get("restore_prefixes", True))
    descending = bool(params.get("descending", True))
    preview = context.get("preview", False)
    logger = context["logger"]
    stats = {"folders": 0, "restored": 0, "renamed": 0, "skipped": 0, "max_supported": len(FOLDER_SIZE_PREFIXES)}

    folders = [path for path in sorted(input_dir.iterdir(), key=lambda item: item.name.lower()) if path.is_dir()]
    if restore_prefixes:
        for folder in list(folders):
            context["check_cancel"]()
            if not has_size_rank_prefix(folder.name):
                continue
            target = input_dir / folder.name[2:]
            if path_exists(target):
                logger.warning("Folder prefix restore skipped because target exists", source=str(folder), target=str(target))
                stats["skipped"] += 1
                continue
            stats["restored"] += 1
            if preview:
                logger.info("Preview restore folder rank prefix", source=str(folder), target=str(target))
            else:
                os.rename(system_path(folder), system_path(fit_path_length(target)))
                logger.info("Restored folder rank prefix", source=str(folder), target=str(target))

    folders = [path for path in sorted(input_dir.iterdir(), key=lambda item: item.name.lower()) if path.is_dir()]
    folders_with_size = []
    for folder in folders:
        context["check_cancel"]()
        size = folder_size_bytes(folder)
        folders_with_size.append((folder, size))
        logger.info("Folder size scanned", folder=str(folder), size_bytes=size)

    folders_with_size.sort(key=lambda item: (item[1], item[0].name.lower()), reverse=descending)
    stats["folders"] = len(folders_with_size)
    if len(folders_with_size) > len(FOLDER_SIZE_PREFIXES):
        logger.warning(
            "Folder count exceeds A-Z/a-z rank prefixes; extra folders are skipped",
            folders=len(folders_with_size),
            max_supported=len(FOLDER_SIZE_PREFIXES),
        )

    planned = []
    for prefix, (folder, size) in zip(FOLDER_SIZE_PREFIXES, folders_with_size):
        base_name = folder.name[2:] if has_size_rank_prefix(folder.name) else folder.name
        target = input_dir / f"{prefix}_{base_name}"
        planned.append((folder, target, size))

    if preview:
        for source, target, size in planned:
            logger.info("Preview folder size rank rename", source=str(source), target=str(target), size_bytes=size)
        return result(True, "文件夹按大小重命名预览完成", str(input_dir), stats)

    temp_pairs = []
    for index, (source, target, size) in enumerate(planned, start=1):
        context["check_cancel"]()
        if source == target:
            logger.info("Folder already has target rank", path=str(source), size_bytes=size)
            continue
        temp = input_dir / f".__rank_tmp_{index:03d}_{source.name}"
        while path_exists(temp):
            temp = unique_path(temp)
        os.rename(system_path(source), system_path(fit_path_length(temp)))
        temp_pairs.append((temp, target, size))

    for temp, target, size in temp_pairs:
        context["check_cancel"]()
        if path_exists(target):
            target = unique_path(target)
        os.rename(system_path(temp), system_path(fit_path_length(target)))
        logger.info("Folder size rank renamed", source=str(temp), target=str(target), size_bytes=size)
        stats["renamed"] += 1

    stats["skipped"] += max(0, len(folders_with_size) - len(FOLDER_SIZE_PREFIXES))
    return result(True, "文件夹按大小重命名完成", str(input_dir), stats)


def filter_files_by_size(params: dict, context: dict) -> dict:
    input_dir = normalize_path(params.get("input_dir"))
    if not input_dir or not input_dir.is_dir():
        raise ValueError("input_dir is required")
    output_dir = normalize_path(params.get("output_dir")) or input_dir / "size_filtered"
    min_size = float(params.get("min_size_mb") or 0) * 1024 * 1024
    preview = context.get("preview", False)
    logger = context["logger"]
    stats = {"matched": 0}
    for src in iter_files(input_dir, recursive=True):
        context["check_cancel"]()
        if output_dir in src.parents:
            continue
        if src.stat().st_size >= min_size:
            dst = output_dir / src.relative_to(input_dir)
            stats["matched"] += 1
            if preview:
                logger.info("Preview size filter copy", source=str(src), target=str(dst))
            else:
                ensure_dir(dst.parent)
                shutil.copy2(system_path(src), system_path(unique_path(fit_path_length(dst))))
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
            os.rename(system_path(src), system_path(unique_path(fit_path_length(dst))))
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
