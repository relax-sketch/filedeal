from __future__ import annotations

from tools import media_tools
from tools.common import result


def run(params: dict, context: dict) -> dict:
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
