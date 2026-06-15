from __future__ import annotations

import shutil
import sys
import tempfile
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.registry import FLOWS, TOOLS
from core.preview import build_preview
from core.path_utils import fit_path_length
from core.runner import resolve_entry
from tools.text_tools import find_anchor_split_position


class MemoryLogger:
    def __init__(self) -> None:
        self.rows: list[tuple[str, str, dict[str, Any]]] = []

    def info(self, message: str, **kwargs: Any) -> None:
        self.rows.append(("info", message, kwargs))

    def warning(self, message: str, **kwargs: Any) -> None:
        self.rows.append(("warning", message, kwargs))

    def error(self, message: str, **kwargs: Any) -> None:
        self.rows.append(("error", message, kwargs))

    def success(self, message: str, **kwargs: Any) -> None:
        self.rows.append(("success", message, kwargs))


def context(preview: bool = False) -> dict[str, Any]:
    logger = MemoryLogger()
    return {
        "task_id": "smoke",
        "logger": logger,
        "settings": {"delete_strategy": "_trash"},
        "preview": preview,
        "check_cancel": lambda: None,
        "set_current_step": lambda step, index=None: logger.info("Step", step=step, index=index),
    }


def write_file(path: Path, data: bytes = b"sample") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return path


def write_text(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def write_image(path: Path, size: tuple[int, int] = (80, 40)) -> Path:
    from PIL import Image

    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", size, color=(32, 96, 160)).save(path)
    return path


def assert_ok(result: dict[str, Any], item_id: str) -> None:
    if not result.get("success", True):
        raise AssertionError(f"{item_id} failed: {result}")


def tool_image_resize(root: Path) -> dict[str, Any]:
    input_dir = root / "input"
    write_image(input_dir / "photo.jpg")
    return {
        "input_dir": str(input_dir),
        "output_dir": str(root / "output"),
        "size_threshold_mb": 0,
        "scale_factor": 0.9,
        "quality": 90,
        "recursive": True,
    }


def tool_rename_and_classify(root: Path) -> dict[str, Any]:
    input_dir = root / "input"
    write_image(input_dir / "nested" / "photo.jpg")
    write_file(input_dir / "nested" / "clip.webm")
    write_file(input_dir / "nested" / "anim.gif")
    write_text(input_dir / "nested" / "note.txt", "note")
    return {"input_dir": str(input_dir), "output_dir": str(root / "classified")}


def tool_split_video_gif(root: Path) -> dict[str, Any]:
    input_dir = root / "input"
    write_file(input_dir / "clip.mp4")
    write_file(input_dir / "anim.gif")
    return {"input_dir": str(input_dir)}


def tool_classify_landscape_images(root: Path) -> dict[str, Any]:
    input_dir = root / "input"
    write_image(input_dir / "wide.jpg", size=(120, 60))
    return {"input_dir": str(input_dir)}


def tool_delete_small_videos(root: Path) -> dict[str, Any]:
    input_dir = root / "input"
    write_file(input_dir / "small.mp4", b"x")
    return {"input_dir": str(input_dir), "min_size_mb": 1, "enable_delete": True}


def tool_delete_low_resolution_videos(root: Path) -> dict[str, Any]:
    input_dir = root / "input"
    write_file(input_dir / "clip.mp4")
    return {"input_dir": str(input_dir)}


def tool_clean_txt_basic(root: Path) -> dict[str, Any]:
    input_dir = root / "input"
    write_text(input_dir / "book.txt", "line\nline\nhttps://example.com\nkeep\n")
    return {"input_dir": str(input_dir), "output_dir": str(root / "cleaned"), "recursive": True}


def tool_clean_txt_ai(root: Path) -> dict[str, Any]:
    input_dir = root / "input"
    write_text(input_dir / "book.txt", "line\n广告\nkeep\n")
    return {"input_dir": str(input_dir), "output_dir": str(root / "cleaned")}


def tool_split_txt_near_size(root: Path) -> dict[str, Any]:
    input_file = write_text(root / "book.txt", ("alpha beta gamma\n" * 80))
    return {"input_file": str(input_file), "output_dir": str(root / "chunks"), "target_chars": 80, "tolerance": 20}


def tool_search_keyword(root: Path) -> dict[str, Any]:
    input_dir = root / "input"
    write_text(input_dir / "a.txt", "alpha alpha beta")
    write_text(input_dir / "b.txt", "beta")
    return {"input_dir": str(input_dir), "keyword": "alpha", "top_n": 5}


def tool_replace_names(root: Path) -> dict[str, Any]:
    input_file = write_text(root / "book.txt", "Alice met Alice.")
    return {"input_file": str(input_file), "output_file": str(root / "out.txt"), "mapping_text": "Alice=>Bob"}


def tool_split_novel_by_anchor(root: Path) -> dict[str, Any]:
    input_file = write_text(root / "novel.txt", "Chapter 1\nalpha\nChapter 2\nbeta\n")
    return {"input_file": str(input_file), "output_dir": str(root / "chapters"), "anchor_text": "Chapter 1\nChapter 2"}


def tool_group_files(root: Path) -> dict[str, Any]:
    input_dir = root / "input"
    for idx in range(3):
        write_file(input_dir / f"{idx}.dat")
    return {"input_dir": str(input_dir), "files_per_group": 2}


def tool_split_large_folder(root: Path) -> dict[str, Any]:
    return tool_group_files(root)


def tool_sort_folders_by_size_rename(root: Path) -> dict[str, Any]:
    input_dir = root / "input"
    write_file(input_dir / "small" / "nested" / "a.bin", b"1")
    write_file(input_dir / "medium" / "a.bin", b"12")
    write_file(input_dir / "large" / "nested" / "a.bin", b"1234")
    return {"input_dir": str(input_dir), "descending": True, "restore_prefixes": True}


def tool_filter_files_by_size(root: Path) -> dict[str, Any]:
    input_dir = root / "input"
    write_file(input_dir / "nested" / "a.bin", b"123")
    write_file(input_dir / "nested" / "b.bin", b"456")
    return {"input_dir": str(input_dir), "output_dir": str(root / "filtered"), "min_size_mb": 0}


def tool_batch_change_extension(root: Path) -> dict[str, Any]:
    input_dir = root / "input"
    write_file(input_dir / "a.txt")
    write_file(input_dir / "b.dat")
    return {"input_dir": str(input_dir), "extension": ".rar"}


def tool_delete_empty_folders(root: Path) -> dict[str, Any]:
    input_dir = root / "input"
    (input_dir / "empty").mkdir(parents=True)
    write_file(input_dir / "nonempty" / "file.txt")
    return {"input_dir": str(input_dir), "enable_delete": True}


def flow_media_clean_standard(root: Path) -> dict[str, Any]:
    input_dir = root / "media"
    write_image(input_dir / "set_a" / "photo.jpg")
    write_file(input_dir / "set_a" / "clip.mp4")
    write_file(input_dir / "set_b" / "anim.gif")
    write_image(input_dir / "set_b" / "photo.png")
    return {
        "input_dir": str(input_dir),
        "output_dir": str(root / "media_out"),
        "batch_subfolders": True,
        "enable_resize": True,
        "enable_delete": False,
        "size_threshold_mb": 999,
        "scale_factor": 0.95,
        "quality": 95,
        "recursive": False,
    }


def flow_txt_clean_split(root: Path) -> dict[str, Any]:
    input_dir = root / "txt"
    write_text(input_dir / "book.txt", ("alpha\n" * 120) + "https://example.com\n")
    return {"input_dir": str(input_dir), "output_dir": str(root / "txt_out"), "target_chars": 80, "tolerance": 20}


def flow_name_replace(root: Path) -> dict[str, Any]:
    return tool_replace_names(root)


def flow_folder_group(root: Path) -> dict[str, Any]:
    return tool_group_files(root)


TOOL_CASES: dict[str, Callable[[Path], dict[str, Any]]] = {
    "image_resize": tool_image_resize,
    "rename_and_classify": tool_rename_and_classify,
    "split_video_gif": tool_split_video_gif,
    "classify_landscape_images": tool_classify_landscape_images,
    "delete_small_videos": tool_delete_small_videos,
    "delete_low_resolution_videos": tool_delete_low_resolution_videos,
    "clean_txt_basic": tool_clean_txt_basic,
    "clean_txt_ai": tool_clean_txt_ai,
    "split_txt_near_size": tool_split_txt_near_size,
    "search_keyword": tool_search_keyword,
    "replace_names": tool_replace_names,
    "split_novel_by_anchor": tool_split_novel_by_anchor,
    "group_files": tool_group_files,
    "split_large_folder": tool_split_large_folder,
    "sort_folders_by_size_rename": tool_sort_folders_by_size_rename,
    "filter_files_by_size": tool_filter_files_by_size,
    "batch_change_extension": tool_batch_change_extension,
    "delete_empty_folders": tool_delete_empty_folders,
}

FLOW_CASES: dict[str, Callable[[Path], dict[str, Any]]] = {
    "media_clean_standard": flow_media_clean_standard,
    "txt_clean_split": flow_txt_clean_split,
    "name_replace": flow_name_replace,
    "folder_group": flow_folder_group,
}


def run_case(item: dict[str, Any], params_factory: Callable[[Path], dict[str, Any]], preview: bool) -> None:
    with tempfile.TemporaryDirectory(prefix=f"proton-smoke-{item['id']}-") as tmp:
        root = Path(tmp)
        params = params_factory(root)
        params["preview"] = preview
        before = sorted(path.relative_to(root) for path in root.rglob("*"))
        result = resolve_entry(item["entry"])(params, context(preview=preview))
        assert_ok(result, item["id"])
        if item["id"] == "rename_and_classify" and result["stats"].get("processed", 0) < 4:
            raise AssertionError(f"{item['id']} did not process nested media files: {result}")
        if item["id"] == "rename_and_classify" and not preview:
            output_dir = Path(params["output_dir"])
            names = sorted(path.name for path in output_dir.iterdir() if path.is_file())
            if len(names) < 4 or not all(name[:5].isdigit() and "_" in name for name in names):
                raise AssertionError(f"{item['id']} did not create ordered flat names: {names}")
            if (Path(params["input_dir"]) / "nested").exists():
                raise AssertionError(f"{item['id']} did not move files out of nested folders")
        if item["id"] == "filter_files_by_size" and result["stats"].get("matched", 0) < 2:
            raise AssertionError(f"{item['id']} did not process nested files: {result}")
        if item["id"] == "sort_folders_by_size_rename" and not preview:
            input_dir = Path(params["input_dir"])
            names = sorted(path.name for path in input_dir.iterdir() if path.is_dir())
            expected_names = ["A_large", "B_medium", "C_small"]
            if names != expected_names:
                raise AssertionError(f"{item['id']} did not rank folders by recursive size: {names}")
        if item["id"] == "media_clean_standard" and not preview:
            output_dir = Path(params["output_dir"])
            expected = [
                output_dir / "set_a_分辨率校正",
                output_dir / "set_a_视频",
                output_dir / "set_b_分辨率校正",
            ]
            missing = [str(path) for path in expected if not path.exists()]
            if missing:
                raise AssertionError(f"{item['id']} did not create named output dirs: {missing}")
        if preview:
            after = sorted(path.relative_to(root) for path in root.rglob("*"))
            if before != after:
                raise AssertionError(f"{item['id']} preview changed files: before={before}, after={after}")


def run_all(kind: str, items: list[dict[str, Any]], cases: dict[str, Callable[[Path], dict[str, Any]]]) -> None:
    registered = {item["id"] for item in items}
    configured = set(cases)
    missing = sorted(registered - configured)
    extra = sorted(configured - registered)
    if missing or extra:
        raise AssertionError(f"{kind} case mismatch: missing={missing}, extra={extra}")

    by_id = {item["id"]: item for item in items}
    for item_id in sorted(registered):
        usage = by_id[item_id].get("usage") or {}
        required_usage_keys = {"purpose", "input", "input_structure", "input_rules", "output"}
        missing_usage = [key for key in sorted(required_usage_keys) if not usage.get(key)]
        if missing_usage:
            raise AssertionError(f"{kind} {item_id} missing usage fields: {missing_usage}")
        run_case(by_id[item_id], cases[item_id], preview=True)
        run_case(by_id[item_id], cases[item_id], preview=False)
        print(f"OK {kind}: {item_id}")


def run_preview_all(kind: str, items: list[dict[str, Any]], cases: dict[str, Callable[[Path], dict[str, Any]]]) -> None:
    by_id = {item["id"]: item for item in items}
    for item_id in sorted(by_id):
        with tempfile.TemporaryDirectory(prefix=f"proton-preview-{item_id}-") as tmp:
            params = cases[item_id](Path(tmp))
            preview = build_preview(kind, item_id, params)
            markdown = preview.get("markdown", "")
            if not markdown.strip():
                raise AssertionError(f"{kind} {item_id} preview is empty")
            if item_id == "media_clean_standard" and "横屏" not in markdown:
                raise AssertionError(f"{item_id} preview missing orientation tree: {markdown}")
            if item_id == "split_video_gif" and "gif" not in markdown:
                raise AssertionError(f"{item_id} preview missing gif folder: {markdown}")
            print(f"OK {kind} preview: {item_id}")


def test_anchor_split_position_priority() -> None:
    text = "第一章内容结束。第二章 新章开始\n正文"
    anchor_pos = text.index("第二章")
    if find_anchor_split_position(text, anchor_pos, 20) != text.index("。") + 1:
        raise AssertionError("Anchor split should fall back to punctuation before anchor")

    text = "第一章内容结束。\n第二章 新章开始\n正文"
    anchor_pos = text.index("第二章")
    if find_anchor_split_position(text, anchor_pos, 20) != anchor_pos:
        raise AssertionError("Anchor split should prefer newline before anchor")


def test_fit_path_length_for_windows_targets() -> None:
    root = Path("C:/very_long_root") / ("nested_" * 12)
    target = root / ("x" * 220 + ".jpg")
    fitted = fit_path_length(target)
    if len(str(fitted)) > 240:
        raise AssertionError(f"fit_path_length did not shorten target enough: {len(str(fitted))}")
    if fitted.suffix != ".jpg":
        raise AssertionError("fit_path_length should preserve the file suffix")


def main() -> None:
    test_anchor_split_position_priority()
    test_fit_path_length_for_windows_targets()
    run_preview_all("tool", TOOLS, TOOL_CASES)
    run_preview_all("flow", FLOWS, FLOW_CASES)
    run_all("tool", TOOLS, TOOL_CASES)
    run_all("flow", FLOWS, FLOW_CASES)


if __name__ == "__main__":
    main()
