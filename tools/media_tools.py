from __future__ import annotations

import shutil
from pathlib import Path

from core.path_utils import normalize_path, unique_path
from core.safety import delete_or_trash
from tools.common import iter_files, result

IMAGE_SUFFIXES = (".jpg", ".jpeg", ".png", ".webp", ".bmp")
VIDEO_SUFFIXES = (".mp4", ".mov", ".avi", ".mkv", ".wmv", ".m4v")


def _copy_or_move(src: Path, dst: Path, preview: bool, logger, move: bool = False) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    target = unique_path(dst)
    if preview:
        logger.info("Preview file operation", source=str(src), target=str(target), move=move)
        return
    if move:
        shutil.move(str(src), str(target))
    else:
        shutil.copy2(src, target)
    logger.info("File operation", source=str(src), target=str(target), move=move)


def resize_images(params: dict, context: dict) -> dict:
    logger = context["logger"]
    preview = context.get("preview", False)
    input_dir = normalize_path(params.get("input_dir"))
    if not input_dir or not input_dir.is_dir():
        raise ValueError("input_dir is required and must be a folder")
    output_dir = normalize_path(params.get("output_dir")) or input_dir.parent / f"{input_dir.name}_分辨率校正"
    threshold = float(params.get("size_threshold_mb") or 9)
    scale = float(params.get("scale_factor") or 0.95)
    quality = int(params.get("quality") or 98)
    recursive = bool(params.get("recursive"))
    files = iter_files(input_dir, recursive=recursive, suffixes=IMAGE_SUFFIXES)
    stats = {"seen": len(files), "resized": 0, "copied": 0, "failed": 0}

    try:
        from PIL import Image
    except ImportError:
        Image = None

    for src in files:
        context["check_cancel"]()
        rel = src.relative_to(input_dir)
        dst = output_dir / rel
        size_mb = src.stat().st_size / (1024 * 1024)
        if preview:
            logger.info("Preview resize image", path=str(src), size_mb=round(size_mb, 2), output=str(dst))
            continue
        try:
            dst.parent.mkdir(parents=True, exist_ok=True)
            if Image is not None and size_mb > threshold:
                Image.MAX_IMAGE_PIXELS = None
                with Image.open(src) as image:
                    width, height = image.size
                    if width >= 2000 or height >= 2000:
                        new_size = (max(1, int(width * scale)), max(1, int(height * scale)))
                        image = image.resize(new_size)
                    image.save(dst, quality=quality, optimize=True)
                stats["resized"] += 1
                logger.info("Resized image", source=str(src), target=str(dst))
            else:
                shutil.copy2(src, dst)
                stats["copied"] += 1
                logger.info("Copied image", source=str(src), target=str(dst))
        except Exception as exc:
            stats["failed"] += 1
            logger.error("Image failed", path=str(src), error=str(exc))
    return result(True, "图片降分辨率完成", str(output_dir), stats)


def rename_and_classify(params: dict, context: dict) -> dict:
    input_dir = normalize_path(params.get("input_dir"))
    if not input_dir or not input_dir.is_dir():
        raise ValueError("input_dir is required")
    output_dir = normalize_path(params.get("output_dir")) or input_dir / "classified"
    logger = context["logger"]
    preview = context.get("preview", False)
    files = iter_files(input_dir)
    stats = {"processed": 0}
    for index, src in enumerate(files, start=1):
        context["check_cancel"]()
        if output_dir in src.parents:
            continue
        category = "videos" if src.suffix.lower() in VIDEO_SUFFIXES else "images" if src.suffix.lower() in IMAGE_SUFFIXES else "other"
        dst = output_dir / category / f"{index:05d}{src.suffix.lower()}"
        _copy_or_move(src, dst, preview, logger, move=False)
        stats["processed"] += 1
    return result(True, "重命名与分类完成", str(output_dir), stats)


def split_video_gif(params: dict, context: dict) -> dict:
    input_dir = normalize_path(params.get("input_dir"))
    if not input_dir or not input_dir.is_dir():
        raise ValueError("input_dir is required")
    logger = context["logger"]
    preview = context.get("preview", False)
    stats = {"videos": 0, "gifs": 0}
    for src in iter_files(input_dir):
        context["check_cancel"]()
        suffix = src.suffix.lower()
        if suffix in VIDEO_SUFFIXES:
            _copy_or_move(src, input_dir / "videos" / src.name, preview, logger, move=False)
            stats["videos"] += 1
        elif suffix == ".gif":
            _copy_or_move(src, input_dir / "gifs" / src.name, preview, logger, move=False)
            stats["gifs"] += 1
    return result(True, "视频/GIF 分离完成", str(input_dir), stats)


def classify_landscape_images(params: dict, context: dict) -> dict:
    input_dir = normalize_path(params.get("input_dir"))
    if not input_dir or not input_dir.is_dir():
        raise ValueError("input_dir is required")
    logger = context["logger"]
    preview = context.get("preview", False)
    stats = {"landscape": 0, "failed": 0}
    try:
        from PIL import Image
    except ImportError:
        Image = None
    for src in iter_files(input_dir, suffixes=IMAGE_SUFFIXES):
        context["check_cancel"]()
        try:
            is_landscape = True
            if Image is not None:
                with Image.open(src) as image:
                    width, height = image.size
                    is_landscape = width >= height
            if is_landscape:
                _copy_or_move(src, input_dir / "横屏" / src.name, preview, logger, move=False)
                stats["landscape"] += 1
        except Exception as exc:
            stats["failed"] += 1
            logger.error("Landscape classify failed", path=str(src), error=str(exc))
    return result(True, "横屏图片分类完成", str(input_dir / "横屏"), stats)


def delete_small_videos(params: dict, context: dict) -> dict:
    input_dir = normalize_path(params.get("input_dir"))
    if not input_dir or not input_dir.is_dir():
        raise ValueError("input_dir is required")
    threshold = float(params.get("min_size_mb") or 1) * 1024 * 1024
    enabled = bool(params.get("enable_delete"))
    preview = context.get("preview", False)
    logger = context["logger"]
    stats = {"candidates": 0, "deleted": 0, "skipped": 0}
    for src in iter_files(input_dir, recursive=True, suffixes=VIDEO_SUFFIXES):
        context["check_cancel"]()
        if src.stat().st_size < threshold:
            stats["candidates"] += 1
            if enabled:
                if delete_or_trash(src, context["settings"], logger, preview=preview):
                    stats["deleted"] += 1
            else:
                logger.info("Delete skipped because enable_delete=false", path=str(src))
                stats["skipped"] += 1
    return result(True, "小视频清理完成", str(input_dir), stats)


def delete_low_resolution_videos(params: dict, context: dict) -> dict:
    input_dir = normalize_path(params.get("input_dir"))
    if not input_dir or not input_dir.is_dir():
        raise ValueError("input_dir is required")
    files = iter_files(input_dir, recursive=True, suffixes=VIDEO_SUFFIXES)
    for src in files:
        context["logger"].info("Video candidate", path=str(src))
    return result(True, "低分辨率视频候选记录完成", str(input_dir), {"candidates": len(files)})
