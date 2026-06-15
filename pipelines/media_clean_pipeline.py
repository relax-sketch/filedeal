from __future__ import annotations

from core.path_utils import normalize_path
from tools import media_tools
from tools.common import result


def _run_one(params: dict, context: dict) -> dict:
    logger = context["logger"]
    stats = {}
    context["set_current_step"]("递归重命名", 1)
    stats["rename"] = media_tools.rename_and_classify(params, context)["stats"]

    context["set_current_step"]("视频/GIF 分离", 2)
    stats["split_video_gif"] = media_tools.split_video_gif(params, context)["stats"]

    context["set_current_step"]("图片横屏分类", 3)
    stats["landscape"] = media_tools.classify_landscape_images(params, context)["stats"]

    if params.get("enable_resize", True):
        context["set_current_step"]("图片降分辨率", 4)
        stats["resize"] = media_tools.resize_images(params, context)["stats"]
    else:
        logger.info("Resize skipped by option")

    context["set_current_step"]("清理小视频文件", 5)
    if params.get("enable_delete"):
        stats["delete_small_videos"] = media_tools.delete_small_videos(params, context)["stats"]
    else:
        logger.info("Delete cleanup skipped because enable_delete=false")
        stats["delete_small_videos"] = {"skipped": True}

    output = params.get("output_dir") or params.get("input_dir") or ""
    return result(True, "图片视频整理标准流程完成", output, stats)


def run(params: dict, context: dict) -> dict:
    if not params.get("batch_subfolders"):
        return _run_one(params, context)

    input_dir = normalize_path(params.get("input_dir"))
    if not input_dir or not input_dir.is_dir():
        raise ValueError("input_dir is required")

    output_dir = normalize_path(params.get("output_dir"))
    children = [path for path in sorted(input_dir.iterdir()) if path.is_dir()]
    if output_dir:
        output_resolved = output_dir.resolve()
        children = [path for path in children if path.resolve() != output_resolved]

    stats = {"folders": 0, "children": {}}
    for child in children:
        context["check_cancel"]()
        child_params = dict(params)
        child_params["batch_subfolders"] = False
        child_params["input_dir"] = str(child)
        if output_dir:
            child_params["output_dir"] = str(output_dir / child.name)
        context["logger"].info("Batch media folder", input_dir=str(child), output_dir=child_params.get("output_dir", ""))
        child_result = _run_one(child_params, context)
        stats["folders"] += 1
        stats["children"][child.name] = child_result["stats"]

    output = str(output_dir or input_dir)
    return result(True, "图片视频整理标准流程批量处理完成", output, stats)
