from __future__ import annotations

from pathlib import Path

from core.path_utils import normalize_path
from tools import text_tools
from tools.common import iter_files, result


def run(params: dict, context: dict) -> dict:
    input_dir = normalize_path(params.get("input_dir"))
    if not input_dir or not input_dir.is_dir():
        raise ValueError("input_dir is required")
    output_dir = normalize_path(params.get("output_dir")) or input_dir.parent / f"{input_dir.name}_clean_split"
    clean_dir = output_dir / "cleaned"
    chunks_dir = output_dir / "chunks"
    context["set_current_step"]("TXT 清洗", 1)
    clean_params = dict(params)
    clean_params["output_dir"] = str(clean_dir)
    if params.get("clean_mode") == "ai":
        clean_result = text_tools.clean_txt_ai(clean_params, context)
    else:
        clean_result = text_tools.clean_txt_basic(clean_params, context)

    context["set_current_step"]("按目标字数切分", 2)
    split_stats = {"files": 0, "chunks": 0}
    for cleaned_file in iter_files(clean_dir, recursive=True, suffixes=(".txt",)):
        context["check_cancel"]()
        rel_parent = cleaned_file.parent.relative_to(clean_dir)
        split_params = {
            "input_file": str(cleaned_file),
            "output_dir": str(chunks_dir / rel_parent / cleaned_file.stem),
            "target_chars": params.get("target_chars", 3300),
            "tolerance": params.get("tolerance", 500),
            "preview": params.get("preview", False),
        }
        split_result = text_tools.split_txt_near_size(split_params, context)
        split_stats["files"] += 1
        split_stats["chunks"] += split_result["stats"].get("chunks", 0)

    context["set_current_step"]("生成日志", 3)
    return result(
        True,
        "TXT 清洗 + 切分流程完成",
        str(output_dir),
        {"clean": clean_result["stats"], "split": split_stats},
    )
