from __future__ import annotations

import shutil
import stat
from pathlib import Path

from core.path_utils import normalize_path
from tools import media_tools
from tools.common import result


OUTPUT_SUFFIXES = ("_分辨率校正", "_视频", "_整理中")


def _unit_output_dirs(input_dir, output_base):
    base = output_base or input_dir.parent
    name = input_dir.name
    return {
        "base": base,
        "workspace": base / f"{name}_整理中",
        "images": base / f"{name}_分辨率校正",
        "videos": base / f"{name}_视频",
    }


def _is_generated_output_dir(path) -> bool:
    return any(path.name.endswith(suffix) for suffix in OUTPUT_SUFFIXES)


def _remove_workspace_if_done(path, context: dict, max_remaining_files: int = 9) -> bool:
    if not path.exists():
        return False
    remaining_files = [item for item in path.rglob("*") if item.is_file()]
    if len(remaining_files) > max_remaining_files:
        return False
    if context.get("preview", False):
        context["logger"].info("Preview remove small workspace", path=str(path), files=len(remaining_files))
        return True
    def handle_remove_error(func, failed_path, exc_info):
        try:
            failed = Path(failed_path)
            failed.chmod(stat.S_IWRITE)
            func(failed_path)
        except Exception as exc:
            context["logger"].warning("Workspace cleanup failed", path=str(failed_path), error=str(exc))

    shutil.rmtree(path, onerror=handle_remove_error)
    context["logger"].info("Removed small workspace", path=str(path), files=len(remaining_files))
    return True


def _run_one(params: dict, context: dict) -> dict:
    logger = context["logger"]
    stats = {}
    input_dir = normalize_path(params.get("input_dir"))
    if not input_dir or not input_dir.is_dir():
        raise ValueError("input_dir is required")
    output_base = normalize_path(params.get("output_dir"))
    dirs = _unit_output_dirs(input_dir, output_base)
    workspace = dirs["workspace"] if output_base else input_dir

    context["set_current_step"]("递归重命名", 1)
    rename_params = dict(params)
    rename_params["input_dir"] = str(input_dir)
    rename_params["output_dir"] = str(workspace)
    rename_params["move_files"] = True
    stats["rename"] = media_tools.rename_and_classify(rename_params, context)["stats"]

    step_workspace = workspace if workspace.exists() else input_dir
    step_params = dict(params)
    step_params["input_dir"] = str(step_workspace)

    context["set_current_step"]("视频/GIF 分离", 2)
    split_params = dict(step_params)
    split_params["output_dir"] = str(dirs["videos"])
    stats["split_video_gif"] = media_tools.split_video_gif(split_params, context)["stats"]

    context["set_current_step"]("视频横竖屏分类", 3)
    video_params = dict(step_params)
    video_input = dirs["videos"] if dirs["videos"].exists() else step_workspace
    video_params["input_dir"] = str(video_input)
    video_params["output_dir"] = str(dirs["videos"])
    stats["video_orientation"] = media_tools.classify_video_orientation(video_params, context)["stats"]

    context["set_current_step"]("图片横竖屏分类", 4)
    image_params = dict(step_params)
    image_params["output_dir"] = str(step_workspace)
    image_params["classify_portrait"] = True
    stats["landscape"] = media_tools.classify_landscape_images(image_params, context)["stats"]

    if params.get("enable_resize", True):
        context["set_current_step"]("图片降分辨率", 5)
        resize_params = dict(step_params)
        resize_params["output_dir"] = str(dirs["images"])
        resize_params["recursive"] = True
        resize_params["move_files"] = True
        stats["resize"] = media_tools.resize_images(resize_params, context)["stats"]
    else:
        logger.info("Resize skipped by option")

    context["set_current_step"]("清理小视频文件", 6)
    if params.get("enable_delete"):
        delete_params = dict(step_params)
        delete_params["input_dir"] = str(dirs["videos"])
        stats["delete_small_videos"] = media_tools.delete_small_videos(delete_params, context)["stats"]
    else:
        logger.info("Delete cleanup skipped because enable_delete=false")
        stats["delete_small_videos"] = {"skipped": True}

    stats["cleanup"] = {
        "workspace_empty_dirs_removed": media_tools.remove_empty_dirs(step_workspace, context),
        "workspace_removed": _remove_workspace_if_done(step_workspace, context),
    }
    output = str(dirs["base"])
    return result(True, "图片视频整理标准流程完成", output, stats)


def run(params: dict, context: dict) -> dict:
    if not params.get("batch_subfolders"):
        return _run_one(params, context)

    input_dir = normalize_path(params.get("input_dir"))
    if not input_dir or not input_dir.is_dir():
        raise ValueError("input_dir is required")

    output_dir = normalize_path(params.get("output_dir"))
    children = [path for path in sorted(input_dir.iterdir()) if path.is_dir() and not _is_generated_output_dir(path)]
    if output_dir:
        output_resolved = output_dir.resolve()
        children = [path for path in children if path.resolve() != output_resolved]

    stats = {"folders": 0, "children": {}}
    if not children:
        video_dirs = [path for path in sorted(input_dir.iterdir()) if path.is_dir() and path.name.endswith("_视频")]
        for video_dir in video_dirs:
            context["check_cancel"]()
            context["logger"].info("Reclassify generated video folder", input_dir=str(video_dir))
            stats["children"][video_dir.name] = {
                "video_orientation": media_tools.classify_video_orientation(
                    {"input_dir": str(video_dir), "output_dir": str(video_dir)},
                    context,
                )["stats"]
            }
            stats["folders"] += 1
        return result(True, "图片视频整理标准流程已整理现有视频目录", str(input_dir), stats)

    for child in children:
        context["check_cancel"]()
        child_params = dict(params)
        child_params["batch_subfolders"] = False
        child_params["input_dir"] = str(child)
        if output_dir:
            child_params["output_dir"] = str(output_dir)
        context["logger"].info("Batch media folder", input_dir=str(child), output_dir=child_params.get("output_dir", ""))
        child_result = _run_one(child_params, context)
        stats["folders"] += 1
        stats["children"][child.name] = child_result["stats"]

    output = str(output_dir or input_dir)
    return result(True, "图片视频整理标准流程批量处理完成", output, stats)
