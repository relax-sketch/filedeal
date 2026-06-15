from __future__ import annotations

import re
from pathlib import Path

from core.path_utils import fit_path_length, normalize_path
from tools.common import iter_files, read_text_any, result, write_text_file


DROP_PATTERNS = [
    r"https?://\S+",
    r"www\.[^\s，。；、]+",
    r"(?:广告|推广|最新网址|最新地址|请收藏|加入书签|TXT下载|免费阅读)",
]

ANCHOR_PUNCTUATION = "。！？!?；;：:"


def clean_text(text: str, aggressive: bool = False) -> tuple[str, dict]:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    kept: list[str] = []
    stats = {"input_lines": 0, "dropped_lines": 0, "output_lines": 0}
    previous_blank = False
    previous_line = ""
    for raw in text.split("\n"):
        stats["input_lines"] += 1
        line = re.sub(r"[\u200b-\u200f\ufeff]", "", raw).strip()
        if any(re.search(pattern, line, re.IGNORECASE) for pattern in DROP_PATTERNS):
            stats["dropped_lines"] += 1
            continue
        if aggressive and len(line) < 4 and not re.search(r"[\u4e00-\u9fffA-Za-z0-9]", line):
            stats["dropped_lines"] += 1
            continue
        if not line:
            if not previous_blank and kept:
                kept.append("")
                previous_blank = True
            continue
        if line == previous_line:
            stats["dropped_lines"] += 1
            continue
        kept.append(line)
        previous_line = line
        previous_blank = False
    cleaned = "\n".join(kept).strip() + "\n"
    stats["output_lines"] = len(cleaned.splitlines())
    return cleaned, stats


def clean_txt_basic(params: dict, context: dict) -> dict:
    input_dir = normalize_path(params.get("input_dir"))
    if not input_dir or not input_dir.is_dir():
        raise ValueError("input_dir is required")
    output_dir = normalize_path(params.get("output_dir")) or input_dir.parent / f"{input_dir.name}_清洗后"
    recursive = bool(params.get("recursive"))
    aggressive = bool(params.get("aggressive"))
    preview = context.get("preview", False)
    logger = context["logger"]
    files = iter_files(input_dir, recursive=recursive, suffixes=(".txt",))
    totals = {"files": 0, "input_lines": 0, "dropped_lines": 0, "output_lines": 0}
    for src in files:
        context["check_cancel"]()
        rel = src.relative_to(input_dir)
        dst = output_dir / rel
        text, encoding = read_text_any(src)
        cleaned, stats = clean_text(text, aggressive=aggressive)
        totals["files"] += 1
        for key in ("input_lines", "dropped_lines", "output_lines"):
            totals[key] += stats[key]
        if preview:
            logger.info("Preview TXT clean", file=str(src), encoding=encoding, output=str(dst), dropped=stats["dropped_lines"])
        else:
            write_text_file(fit_path_length(dst), cleaned, encoding="utf-8", newline="\n")
            logger.info("Cleaned TXT", file=str(src), output=str(dst), encoding=encoding)
    return result(True, "TXT 清洗完成", str(output_dir), totals)


def clean_txt_ai(params: dict, context: dict) -> dict:
    params = dict(params)
    params["aggressive"] = True
    return clean_txt_basic(params, context)


def find_split_index(text: str, start: int, target_size: int, tolerance: int) -> int:
    target_pos = min(start + target_size, len(text))
    left = max(start + 1, target_pos - tolerance)
    right = min(len(text), target_pos + tolerance)
    candidates = [pos for pos in (text.rfind("\n", left, target_pos), text.find("\n", target_pos, right)) if pos != -1]
    if candidates:
        return min(candidates, key=lambda pos: abs(pos - target_pos)) + 1
    return min(start + target_size, len(text))


def split_text(text: str, target_size: int, tolerance: int) -> list[str]:
    chunks = []
    start = 0
    while start < len(text):
        end = find_split_index(text, start, target_size, tolerance)
        if end <= start:
            end = min(start + target_size, len(text))
        chunks.append(text[start:end])
        start = end
    return chunks


def split_txt_near_size(params: dict, context: dict) -> dict:
    input_file = normalize_path(params.get("input_file"))
    if not input_file or not input_file.is_file():
        raise ValueError("input_file is required")
    output_dir = normalize_path(params.get("output_dir")) or input_file.parent / f"{input_file.stem}_chunks"
    target = int(params.get("target_chars") or 3300)
    tolerance = int(params.get("tolerance") or 500)
    text, encoding = read_text_any(input_file)
    chunks = split_text(text, target, tolerance)
    if context.get("preview"):
        context["logger"].info("Preview split TXT", file=str(input_file), chunks=len(chunks), encoding=encoding)
    else:
        for idx, chunk in enumerate(chunks, start=1):
            write_text_file(fit_path_length(output_dir / f"{input_file.stem}_{idx:03d}.txt"), chunk, encoding="utf-8")
    return result(True, "TXT 切分完成", str(output_dir), {"chunks": len(chunks)})


def search_keyword(params: dict, context: dict) -> dict:
    input_dir = normalize_path(params.get("input_dir"))
    keyword = str(params.get("keyword") or "")
    if not input_dir or not input_dir.is_dir() or not keyword:
        raise ValueError("input_dir and keyword are required")
    top_n = int(params.get("top_n") or 10)
    rows = []
    for src in iter_files(input_dir, recursive=True, suffixes=(".txt",)):
        text, _ = read_text_any(src)
        count = text.lower().count(keyword.lower())
        if count:
            rows.append({"path": str(src), "count": count})
    rows.sort(key=lambda item: item["count"], reverse=True)
    rows = rows[:top_n]
    for row in rows:
        context["logger"].info("Keyword hit", **row)
    return result(True, "关键词搜索完成", str(input_dir), {"matches": len(rows)}, file_operations=rows)


def parse_mapping(mapping_text: str) -> dict[str, str]:
    mapping = {}
    for line in mapping_text.splitlines():
        if "=>" not in line:
            continue
        old, new = line.split("=>", 1)
        old = old.strip()
        if old:
            mapping[old] = new.strip()
    return mapping


def replace_names(params: dict, context: dict) -> dict:
    input_file = normalize_path(params.get("input_file"))
    if not input_file or not input_file.is_file():
        raise ValueError("input_file is required")
    output_file = normalize_path(params.get("output_file")) or input_file.with_name(f"{input_file.stem}_replaced.txt")
    mapping = parse_mapping(str(params.get("mapping_text") or ""))
    if not mapping:
        raise ValueError("mapping_text must contain old=>new lines")
    text, _ = read_text_any(input_file)
    counts = {}
    for old, new in mapping.items():
        count = text.count(old)
        counts[old] = count
        text = text.replace(old, new)
    if context.get("preview"):
        context["logger"].info("Preview name replace", output=str(output_file), counts=counts)
    else:
        write_text_file(fit_path_length(output_file), text, encoding="utf-8")
    return result(True, "人物名替换完成", str(output_file), {"replacements": counts})


def _nearest_position(candidates: list[int], target: int) -> int | None:
    if not candidates:
        return None
    return min(candidates, key=lambda candidate: abs(candidate - target))


def find_anchor_split_position(text: str, anchor_pos: int, window_chars: int) -> int:
    window_chars = max(0, window_chars)
    left = max(0, anchor_pos - window_chars)
    right = min(len(text), anchor_pos + window_chars)

    newline_positions = [0] if anchor_pos == 0 else []
    newline_positions.extend(idx + 1 for idx in range(left, right) if text[idx] == "\n")
    punctuation_positions = [idx + 1 for idx in range(left, right) if text[idx] in ANCHOR_PUNCTUATION]
    priority_groups = (
        [pos for pos in newline_positions if pos <= anchor_pos],
        [pos for pos in punctuation_positions if pos <= anchor_pos],
        [pos for pos in newline_positions if pos > anchor_pos],
        [pos for pos in punctuation_positions if pos > anchor_pos],
    )
    for candidates in priority_groups:
        split_pos = _nearest_position(candidates, anchor_pos)
        if split_pos is not None:
            return split_pos

    return anchor_pos


def split_novel_by_anchor(params: dict, context: dict) -> dict:
    input_file = normalize_path(params.get("input_file"))
    if not input_file or not input_file.is_file():
        raise ValueError("input_file is required")
    output_dir = normalize_path(params.get("output_dir")) or input_file.parent / f"{input_file.stem}_chapters"
    anchor_text = str(params.get("anchor_text") or "").strip()
    window_chars = int(params.get("search_window_chars") or 120)
    text, _ = read_text_any(input_file)
    anchors = [line.strip() for line in anchor_text.splitlines() if line.strip()]
    if not anchors:
        anchors = re.findall(r"^第.{1,12}[章节回].*$", text, re.MULTILINE)
    chunks = []
    if anchors:
        positions = sorted({
            find_anchor_split_position(text, pos, window_chars)
            for anchor in anchors
            for pos in [text.find(anchor)]
            if pos >= 0
        })
        for idx, pos in enumerate(positions):
            end = positions[idx + 1] if idx + 1 < len(positions) else len(text)
            chunks.append(text[pos:end])
    else:
        chunks = [text]
    if not context.get("preview"):
        for idx, chunk in enumerate(chunks, start=1):
            write_text_file(fit_path_length(output_dir / f"chapter_{idx:03d}.txt"), chunk, encoding="utf-8")
    return result(True, "章节切分完成", str(output_dir), {"chapters": len(chunks)})
