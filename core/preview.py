from __future__ import annotations

from pathlib import Path
from typing import Callable

from core.path_utils import normalize_path
from core.registry import get_flow, get_tool


def _resolve_item(kind: str, item_id: str) -> dict:
    item = get_tool(item_id) if kind == "tool" else get_flow(item_id)
    if item is None:
        raise KeyError(item_id)
    return item


def _input_dir(params: dict) -> Path:
    path = normalize_path(params.get("input_dir"))
    if not path or not path.is_dir():
        raise ValueError("input_dir is required")
    return path


def _input_file(params: dict) -> Path:
    path = normalize_path(params.get("input_file"))
    if not path or not path.is_file():
        raise ValueError("input_file is required")
    return path


def _path_line(label: str, path: Path | None) -> str:
    return f"- {label}: `{path}`" if path else f"- {label}: `<自动生成>`"


def _dir_names(path: Path, *, limit: int = 8, exclude: Callable[[Path], bool] | None = None) -> list[str]:
    exclude = exclude or (lambda _: False)
    names = [
        child.name
        for child in sorted(path.iterdir(), key=lambda item: item.name.lower())
        if child.is_dir() and not exclude(child)
    ]
    if len(names) > limit:
        return names[:limit] + [f"... 其余 {len(names) - limit} 个子目录"]
    return names


def _file_count(path: Path) -> int:
    return len([child for child in path.iterdir() if child.is_file()])


def _tree(root: str, children: list[str]) -> list[str]:
    lines = [f"- `{root}`"]
    lines.extend(f"  - `{child}`" for child in children)
    return lines


def _tree3(root: str, branches: list[tuple[str, list[str]]]) -> list[str]:
    lines = [f"- `{root}`"]
    for branch, children in branches:
        lines.append(f"  - `{branch}`")
        lines.extend(f"    - `{child}`" for child in children)
    return lines


def _media_unit_lines(base: Path, name: str, enable_resize: bool = True) -> list[str]:
    branches: list[tuple[str, list[str]]] = []
    if enable_resize:
        branches.append((f"{name}_分辨率校正", ["横屏", "竖屏"]))
    branches.append((f"{name}_视频", ["横屏", "竖屏", "未知", "gif"]))
    return _tree3(str(base), branches)


def _generated_media_name(path: Path) -> bool:
    return path.name.endswith(("_分辨率校正", "_视频", "_整理中"))


def _preview_image_resize(params: dict) -> dict:
    input_dir = _input_dir(params)
    output_dir = normalize_path(params.get("output_dir")) or input_dir.parent / f"{input_dir.name}_分辨率校正"
    recursive = bool(params.get("recursive"))
    lines = [
        "# 结构预览",
        _path_line("输入目录", input_dir),
        _path_line("输出目录", output_dir),
        f"- 处理方式: `{'递归处理子目录' if recursive else '仅处理当前目录第一层图片'}`",
        "",
        "## 预计目录",
    ]
    children = ["<保留输入目录结构>", "<缩放后的图片文件>"] if recursive else ["<缩放后的图片文件>"]
    lines.extend(_tree(str(output_dir), children))
    return {"markdown": "\n".join(lines), "output_path": str(output_dir)}


def _preview_rename_and_classify(params: dict) -> dict:
    input_dir = _input_dir(params)
    output_dir = normalize_path(params.get("output_dir")) or input_dir
    lines = [
        "# 结构预览",
        _path_line("输入目录", input_dir),
        _path_line("输出目录", output_dir),
        "- 处理方式: `递归提取全部子目录文件，扁平化后按序重命名`",
        "",
        "## 预计目录",
    ]
    lines.extend(_tree(str(output_dir), ["00001_父目录_原文件名.ext", "00002_父目录_原文件名.ext", "..."]))
    return {"markdown": "\n".join(lines), "output_path": str(output_dir)}


def _preview_split_video_gif(params: dict) -> dict:
    input_dir = _input_dir(params)
    output_dir = normalize_path(params.get("output_dir")) or input_dir / "视频"
    lines = [
        "# 结构预览",
        _path_line("输入目录", input_dir),
        _path_line("输出目录", output_dir),
        "",
        "## 预计目录",
    ]
    lines.extend(_tree(str(output_dir), ["<视频文件>", "gif"]))
    return {"markdown": "\n".join(lines), "output_path": str(output_dir)}


def _preview_classify_landscape_images(params: dict) -> dict:
    input_dir = _input_dir(params)
    output_dir = normalize_path(params.get("output_dir")) or input_dir
    classify_portrait = bool(params.get("classify_portrait"))
    children = ["横屏"] + (["竖屏"] if classify_portrait else [])
    lines = [
        "# 结构预览",
        _path_line("输入目录", input_dir),
        _path_line("输出目录", output_dir),
        "",
        "## 预计目录",
    ]
    lines.extend(_tree(str(output_dir), children))
    return {"markdown": "\n".join(lines), "output_path": str(output_dir)}


def _preview_classify_video_orientation(params: dict) -> dict:
    input_dir = _input_dir(params)
    output_dir = normalize_path(params.get("output_dir")) or input_dir
    lines = [
        "# 结构预览",
        _path_line("输入目录", input_dir),
        _path_line("输出目录", output_dir),
        "",
        "## 预计目录",
    ]
    lines.extend(_tree(str(output_dir), ["横屏", "竖屏", "未知"]))
    return {"markdown": "\n".join(lines), "output_path": str(output_dir)}


def _preview_delete_log_only(params: dict, message: str) -> dict:
    input_dir = _input_dir(params)
    lines = [
        "# 结构预览",
        _path_line("输入目录", input_dir),
        "- 输出方式: `不新建输出目录，只在执行日志中记录候选项或删除结果`",
        f"- 说明: `{message}`",
    ]
    return {"markdown": "\n".join(lines), "output_path": str(input_dir)}


def _preview_clean_txt_basic(params: dict, aggressive: bool = False) -> dict:
    input_dir = _input_dir(params)
    output_dir = normalize_path(params.get("output_dir")) or input_dir.parent / f"{input_dir.name}_清洗后"
    recursive = bool(params.get("recursive"))
    lines = [
        "# 结构预览",
        _path_line("输入目录", input_dir),
        _path_line("输出目录", output_dir),
        f"- 处理方式: `{'递归处理全部子目录 TXT' if recursive else '仅处理当前目录第一层 TXT'}`",
        f"- 清洗强度: `{'强力清洗' if aggressive else '基础清洗'}`",
        "",
        "## 预计目录",
    ]
    children = ["<保留输入目录结构>", "<清洗后的 TXT>"] if recursive else ["<清洗后的 TXT>"]
    lines.extend(_tree(str(output_dir), children))
    return {"markdown": "\n".join(lines), "output_path": str(output_dir)}


def _preview_split_txt_near_size(params: dict) -> dict:
    input_file = _input_file(params)
    output_dir = normalize_path(params.get("output_dir")) or input_file.parent / f"{input_file.stem}_chunks"
    lines = [
        "# 结构预览",
        _path_line("输入文件", input_file),
        _path_line("输出目录", output_dir),
        "",
        "## 预计目录",
    ]
    lines.extend(_tree(str(output_dir), [f"{input_file.stem}_001.txt", f"{input_file.stem}_002.txt", "..."]))
    return {"markdown": "\n".join(lines), "output_path": str(output_dir)}


def _preview_search_keyword(params: dict) -> dict:
    input_dir = _input_dir(params)
    keyword = str(params.get("keyword") or "")
    lines = [
        "# 结构预览",
        _path_line("输入目录", input_dir),
        f"- 关键词: `{keyword}`",
        "- 输出方式: `不新建输出目录，只在执行日志中输出命中文件与次数`",
    ]
    return {"markdown": "\n".join(lines), "output_path": str(input_dir)}


def _preview_replace_names(params: dict) -> dict:
    input_file = _input_file(params)
    output_file = normalize_path(params.get("output_file")) or input_file.with_name(f"{input_file.stem}_replaced.txt")
    lines = [
        "# 结构预览",
        _path_line("输入文件", input_file),
        _path_line("输出文件", output_file),
        "",
        "## 预计输出",
        f"- `{output_file.name}`",
    ]
    return {"markdown": "\n".join(lines), "output_path": str(output_file)}


def _preview_split_novel_by_anchor(params: dict) -> dict:
    input_file = _input_file(params)
    output_dir = normalize_path(params.get("output_dir")) or input_file.parent / f"{input_file.stem}_chapters"
    lines = [
        "# 结构预览",
        _path_line("输入文件", input_file),
        _path_line("输出目录", output_dir),
        "",
        "## 预计目录",
    ]
    lines.extend(_tree(str(output_dir), ["chapter_001.txt", "chapter_002.txt", "..."]))
    return {"markdown": "\n".join(lines), "output_path": str(output_dir)}


def _preview_group_files(params: dict) -> dict:
    input_dir = _input_dir(params)
    per_group = max(1, int(params.get("files_per_group") or 80))
    top_files = _file_count(input_dir)
    estimated_groups = max(1, (top_files + per_group - 1) // per_group) if top_files else 1
    children = [f"group_{index}" for index in range(1, min(estimated_groups, 3) + 1)]
    if estimated_groups > 3:
        children.append("...")
    lines = [
        "# 结构预览",
        _path_line("输入目录", input_dir),
        f"- 每组文件数: `{per_group}`",
        f"- 估计分组数: `{estimated_groups}`",
        "",
        "## 预计目录",
    ]
    lines.extend(_tree(str(input_dir), children or ["group_1"]))
    return {"markdown": "\n".join(lines), "output_path": str(input_dir)}


def _preview_sort_folders_by_size_rename(params: dict) -> dict:
    input_dir = _input_dir(params)
    children = _dir_names(input_dir)
    lines = [
        "# 结构预览",
        _path_line("输入目录", input_dir),
        "- 排序方式: `按递归总大小排序后重命名`",
        "- 输出方式: `原目录内重命名，不新建输出目录`",
        "",
        "## 当前第一层子目录",
    ]
    lines.extend(f"- `{name}`" for name in (children or ["<未找到子目录>"]))
    lines.extend(
        [
            "",
            "## 预计命名格式",
            f"- `A_<按大小排序第1名>`",
            f"- `B_<按大小排序第2名>`",
            f"- `C_<按大小排序第3名>`",
        ]
    )
    return {"markdown": "\n".join(lines), "output_path": str(input_dir)}


def _preview_filter_files_by_size(params: dict) -> dict:
    input_dir = _input_dir(params)
    output_dir = normalize_path(params.get("output_dir")) or input_dir / "size_filtered"
    lines = [
        "# 结构预览",
        _path_line("输入目录", input_dir),
        _path_line("输出目录", output_dir),
        "- 处理方式: `递归筛选并保留原相对目录结构`",
        "",
        "## 预计目录",
    ]
    lines.extend(_tree(str(output_dir), ["<保留输入目录结构>", "<达到大小阈值的文件>"]))
    return {"markdown": "\n".join(lines), "output_path": str(output_dir)}


def _preview_batch_change_extension(params: dict) -> dict:
    input_dir = _input_dir(params)
    extension = str(params.get("extension") or ".rar")
    if not extension.startswith("."):
        extension = "." + extension
    lines = [
        "# 结构预览",
        _path_line("输入目录", input_dir),
        f"- 目标后缀: `{extension}`",
        "- 输出方式: `原目录内直接改名，不新建输出目录`",
        "",
        "## 预计文件名格式",
        f"- `原文件名{extension}`",
    ]
    return {"markdown": "\n".join(lines), "output_path": str(input_dir)}


def _preview_media_clean_standard(params: dict) -> dict:
    input_dir = _input_dir(params)
    output_base = normalize_path(params.get("output_dir")) or input_dir.parent
    batch_subfolders = bool(params.get("batch_subfolders"))
    enable_resize = bool(params.get("enable_resize", True))
    lines = [
        "# 结构预览",
        _path_line("输入目录", input_dir),
        _path_line("输出根目录", output_base),
        "- 说明: `这是目录结构预测，不会执行真实重命名、分类和压缩`",
        "",
        "## 预计目录",
    ]
    if batch_subfolders:
        children = _dir_names(input_dir, exclude=_generated_media_name)
        targets = children if children else ["<子任务1>", "<子任务2>"]
        for child_name in targets:
            lines.extend(_media_unit_lines(output_base, child_name, enable_resize=enable_resize))
    else:
        lines.extend(_media_unit_lines(output_base, input_dir.name, enable_resize=enable_resize))
    return {"markdown": "\n".join(lines), "output_path": str(output_base)}


def _preview_txt_clean_split(params: dict) -> dict:
    input_dir = _input_dir(params)
    output_dir = normalize_path(params.get("output_dir")) or input_dir.parent / f"{input_dir.name}_clean_split"
    lines = [
        "# 结构预览",
        _path_line("输入目录", input_dir),
        _path_line("输出目录", output_dir),
        "",
        "## 预计目录",
    ]
    lines.extend(_tree3(str(output_dir), [("cleaned", ["<保留输入目录结构>"]), ("chunks", ["<每个 TXT 一个子目录>"])]))
    return {"markdown": "\n".join(lines), "output_path": str(output_dir)}


def _preview_name_replace_flow(params: dict) -> dict:
    return _preview_replace_names(params)


def _preview_folder_group_flow(params: dict) -> dict:
    return _preview_group_files(params)


PREVIEW_BUILDERS: dict[str, Callable[[dict], dict]] = {
    "image_resize": _preview_image_resize,
    "rename_and_classify": _preview_rename_and_classify,
    "split_video_gif": _preview_split_video_gif,
    "classify_landscape_images": _preview_classify_landscape_images,
    "classify_video_orientation": _preview_classify_video_orientation,
    "delete_small_videos": lambda params: _preview_delete_log_only(params, "按大小筛选小视频并执行删除策略"),
    "delete_low_resolution_videos": lambda params: _preview_delete_log_only(params, "扫描视频并把低分辨率候选写入日志"),
    "clean_txt_basic": _preview_clean_txt_basic,
    "clean_txt_ai": lambda params: _preview_clean_txt_basic(params, aggressive=True),
    "split_txt_near_size": _preview_split_txt_near_size,
    "search_keyword": _preview_search_keyword,
    "replace_names": _preview_replace_names,
    "split_novel_by_anchor": _preview_split_novel_by_anchor,
    "group_files": _preview_group_files,
    "split_large_folder": _preview_group_files,
    "sort_folders_by_size_rename": _preview_sort_folders_by_size_rename,
    "filter_files_by_size": _preview_filter_files_by_size,
    "batch_change_extension": _preview_batch_change_extension,
    "delete_empty_folders": lambda params: _preview_delete_log_only(params, "递归扫描空目录并根据删除策略处理"),
    "media_clean_standard": _preview_media_clean_standard,
    "txt_clean_split": _preview_txt_clean_split,
    "name_replace": _preview_name_replace_flow,
    "folder_group": _preview_folder_group_flow,
}


def build_preview(kind: str, item_id: str, params: dict) -> dict:
    item = _resolve_item(kind, item_id)
    builder = PREVIEW_BUILDERS.get(item_id)
    if builder is None:
        raise ValueError(f"No preview builder for {item_id}")
    preview = builder(params)
    preview.update(
        {
            "item_id": item_id,
            "kind": kind,
            "name": item["name"],
            "requires_confirmation": True,
        }
    )
    return preview
