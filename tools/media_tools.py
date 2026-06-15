from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

from core.path_utils import normalize_path, unique_path
from core.safety import delete_or_trash
from tools.common import iter_files, result

IMAGE_SUFFIXES = (".jpg", ".jpeg", ".png", ".webp", ".bmp")
VIDEO_SUFFIXES = (
    ".mp4",
    ".mov",
    ".avi",
    ".mkv",
    ".wmv",
    ".m4v",
    ".webm",
    ".flv",
    ".rmvb",
    ".mpeg",
    ".mpg",
    ".3gp",
    ".3g2",
    ".mts",
    ".m2ts",
    ".ts",
    ".vob",
    ".ogv",
)


def _safe_name_part(value: str) -> str:
    cleaned = "".join(ch if ch not in '<>:"/\\|?*' else "_" for ch in value).strip()
    return cleaned or "file"


def _flatten_name(src: Path, input_dir: Path, index: int) -> str:
    rel = src.relative_to(input_dir)
    parts = [_safe_name_part(part) for part in rel.with_suffix("").parts]
    stem = "_".join(parts)
    max_stem = 120
    if len(stem) > max_stem:
        stem = stem[-max_stem:]
    return f"{index:05d}_{stem}{src.suffix.lower()}"


def _remove_empty_dirs(root: Path, logger, preview: bool) -> int:
    removed = 0
    for folder in sorted((path for path in root.rglob("*") if path.is_dir()), key=lambda path: len(path.parts), reverse=True):
        if not folder.exists() or any(folder.iterdir()):
            continue
        if preview:
            logger.info("Preview remove empty folder", path=str(folder))
        else:
            folder.rmdir()
            logger.info("Removed empty folder", path=str(folder))
        removed += 1
    return removed


def remove_empty_dirs(root: Path, context: dict) -> int:
    return _remove_empty_dirs(root, context["logger"], context.get("preview", False))


def _ffprobe_video_size(path: Path) -> tuple[float, float] | None:
    try:
        completed = subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-select_streams",
                "v:0",
                "-show_entries",
                "stream=width,height:stream_tags=rotate:stream_side_data=rotation",
                "-of",
                "json",
                str(path),
            ],
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=10,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if completed.returncode != 0:
        return None
    try:
        data = json.loads(completed.stdout or "{}")
        stream = (data.get("streams") or [{}])[0]
        width = float(stream.get("width") or 0)
        height = float(stream.get("height") or 0)
        rotation = 0.0
        tags = stream.get("tags") or {}
        if tags.get("rotate") not in (None, ""):
            rotation = float(tags.get("rotate") or 0)
        for side_data in stream.get("side_data_list") or []:
            if side_data.get("rotation") not in (None, ""):
                rotation = float(side_data.get("rotation") or 0)
                break
        if width <= 0 or height <= 0:
            return None
        if abs(int(rotation)) % 180 == 90:
            width, height = height, width
        return width, height
    except (ValueError, TypeError, json.JSONDecodeError, IndexError):
        return None


def _cv2_video_size(path: Path) -> tuple[float, float] | None:
    try:
        import cv2
    except ImportError:
        return None
    cap = cv2.VideoCapture(str(path))
    try:
        width = float(cap.get(3) or 0)
        height = float(cap.get(4) or 0)
    finally:
        cap.release()
    if width <= 0 or height <= 0:
        return None
    return width, height


def _video_size(path: Path) -> tuple[float, float] | None:
    return _ffprobe_video_size(path) or _cv2_video_size(path)


def _copy_or_move(src: Path, dst: Path, preview: bool, logger, move: bool = False) -> None:
    target = unique_path(dst)
    if preview:
        logger.info("Preview file operation", source=str(src), target=str(target), move=move)
        return
    dst.parent.mkdir(parents=True, exist_ok=True)
    if move:
        try:
            src.rename(target)
        except OSError:
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
    move_files = bool(params.get("move_files"))
    files = iter_files(input_dir, recursive=recursive, suffixes=IMAGE_SUFFIXES)
    input_resolved = input_dir.resolve()
    output_resolved = output_dir.resolve()
    if output_resolved != input_resolved:
        files = [src for src in files if output_resolved not in src.resolve().parents]
    stats = {"seen": len(files), "resized": 0, "copied": 0, "moved": 0, "removed": 0, "failed": 0}

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
                target = unique_path(dst)
                Image.MAX_IMAGE_PIXELS = None
                with Image.open(src) as image:
                    width, height = image.size
                    if width >= 2000 or height >= 2000:
                        new_size = (max(1, int(width * scale)), max(1, int(height * scale)))
                        image = image.resize(new_size)
                    image.save(target, quality=quality, optimize=True)
                stats["resized"] += 1
                logger.info("Resized image", source=str(src), target=str(target))
            else:
                target = unique_path(dst)
                if move_files:
                    try:
                        src.rename(target)
                    except OSError:
                        shutil.move(str(src), str(target))
                    stats["moved"] += 1
                    logger.info("Moved image", source=str(src), target=str(target))
                else:
                    shutil.copy2(src, target)
                    stats["copied"] += 1
                    logger.info("Copied image", source=str(src), target=str(target))
            if move_files and Image is not None and size_mb > threshold and src.exists():
                src.unlink()
                stats["removed"] += 1
                logger.info("Removed source image", source=str(src))
        except Exception as exc:
            stats["failed"] += 1
            logger.error("Image failed", path=str(src), error=str(exc))
    return result(True, "图片降分辨率完成", str(output_dir), stats)


def rename_and_classify(params: dict, context: dict) -> dict:
    input_dir = normalize_path(params.get("input_dir"))
    if not input_dir or not input_dir.is_dir():
        raise ValueError("input_dir is required")
    output_dir = normalize_path(params.get("output_dir")) or input_dir
    logger = context["logger"]
    preview = context.get("preview", False)
    move_files = params.get("move_files", True)
    files = iter_files(input_dir, recursive=True)
    stats = {"processed": 0, "moved": 0, "copied": 0, "empty_dirs_removed": 0}
    input_resolved = input_dir.resolve()
    output_resolved = output_dir.resolve()
    for index, src in enumerate(files, start=1):
        context["check_cancel"]()
        if output_resolved != input_resolved and output_resolved in src.resolve().parents:
            continue
        dst = output_dir / _flatten_name(src, input_dir, index)
        _copy_or_move(src, dst, preview, logger, move=move_files)
        stats["processed"] += 1
        if move_files:
            stats["moved"] += 1
        else:
            stats["copied"] += 1
    if move_files:
        stats["empty_dirs_removed"] = _remove_empty_dirs(input_dir, logger, preview)
    return result(True, "重命名与分类完成", str(output_dir), stats)


def split_video_gif(params: dict, context: dict) -> dict:
    input_dir = normalize_path(params.get("input_dir"))
    if not input_dir or not input_dir.is_dir():
        raise ValueError("input_dir is required")
    output_dir = normalize_path(params.get("output_dir")) or input_dir / "视频"
    logger = context["logger"]
    preview = context.get("preview", False)
    stats = {"videos": 0, "gifs": 0}
    for src in iter_files(input_dir):
        context["check_cancel"]()
        suffix = src.suffix.lower()
        if suffix in VIDEO_SUFFIXES:
            _copy_or_move(src, output_dir / src.name, preview, logger, move=True)
            stats["videos"] += 1
        elif suffix == ".gif":
            _copy_or_move(src, output_dir / "gif" / src.name, preview, logger, move=True)
            stats["gifs"] += 1
    return result(True, "视频/GIF 分离完成", str(output_dir), stats)


def classify_landscape_images(params: dict, context: dict) -> dict:
    input_dir = normalize_path(params.get("input_dir"))
    if not input_dir or not input_dir.is_dir():
        raise ValueError("input_dir is required")
    output_dir = normalize_path(params.get("output_dir")) or input_dir
    classify_portrait = bool(params.get("classify_portrait"))
    logger = context["logger"]
    preview = context.get("preview", False)
    stats = {"landscape": 0, "portrait": 0, "failed": 0}
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
                _copy_or_move(src, output_dir / "横屏" / src.name, preview, logger, move=True)
                stats["landscape"] += 1
            elif classify_portrait:
                _copy_or_move(src, output_dir / "竖屏" / src.name, preview, logger, move=True)
                stats["portrait"] += 1
        except Exception as exc:
            stats["failed"] += 1
            logger.error("Landscape classify failed", path=str(src), error=str(exc))
    return result(True, "图片横竖屏分类完成", str(output_dir), stats)


def classify_video_orientation(params: dict, context: dict) -> dict:
    input_dir = normalize_path(params.get("input_dir"))
    if not input_dir or not input_dir.is_dir():
        raise ValueError("input_dir is required")
    output_dir = normalize_path(params.get("output_dir")) or input_dir
    preview = context.get("preview", False)
    logger = context["logger"]
    stats = {"landscape": 0, "portrait": 0, "unknown": 0, "failed": 0}

    for src in iter_files(input_dir, recursive=True, suffixes=VIDEO_SUFFIXES):
        context["check_cancel"]()
        rel_parent_parts = set(src.relative_to(input_dir).parts[:-1])
        if output_dir.resolve() == input_dir.resolve() and rel_parent_parts.intersection({"横屏", "竖屏"}):
            continue
        try:
            size = _video_size(src)
            width, height = size if size else (0, 0)
            if height > width > 0:
                folder = "竖屏"
                stats["portrait"] += 1
            elif width >= height > 0:
                folder = "横屏"
                stats["landscape"] += 1
            else:
                folder = "未知"
                stats["unknown"] += 1
            logger.info("Video orientation", path=str(src), width=width, height=height, folder=folder)
            _copy_or_move(src, output_dir / folder / src.name, preview, logger, move=True)
        except Exception as exc:
            stats["failed"] += 1
            logger.error("Video orientation classify failed", path=str(src), error=str(exc))
    return result(True, "视频横竖屏分类完成", str(output_dir), stats)


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
