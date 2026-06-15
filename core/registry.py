from __future__ import annotations

from typing import Any

TOOLS: list[dict[str, Any]] = [
    {
        "id": "image_resize",
        "name": "图片降分辨率",
        "category": "图片视频",
        "description": "压缩或缩放指定文件夹内超过阈值的图片。",
        "risk": "medium",
        "entry": "tools.media_tools:resize_images",
        "supports_preview": True,
        "schema": [
            {"name": "input_dir", "label": "输入文件夹", "type": "path", "required": True},
            {"name": "output_dir", "label": "输出文件夹", "type": "path", "required": False},
            {"name": "size_threshold_mb", "label": "文件大小阈值 MB", "type": "number", "default": 9},
            {"name": "scale_factor", "label": "缩放比例", "type": "number", "default": 0.95},
            {"name": "quality", "label": "保存质量", "type": "number", "default": 98},
            {"name": "recursive", "label": "递归处理", "type": "boolean", "default": False},
        ],
    },
    {
        "id": "rename_and_classify",
        "name": "扁平化重命名与分类",
        "category": "图片视频",
        "description": "按序重命名并按媒体类型分类文件。",
        "risk": "medium",
        "entry": "tools.media_tools:rename_and_classify",
        "supports_preview": True,
        "schema": [
            {"name": "input_dir", "label": "输入文件夹", "type": "path", "required": True},
            {"name": "output_dir", "label": "输出文件夹", "type": "path", "required": False},
        ],
    },
    {
        "id": "split_video_gif",
        "name": "视频/GIF 分离",
        "category": "图片视频",
        "description": "将视频和 GIF 移动到独立子目录。",
        "risk": "medium",
        "entry": "tools.media_tools:split_video_gif",
        "supports_preview": True,
        "schema": [{"name": "input_dir", "label": "输入文件夹", "type": "path", "required": True}],
    },
    {
        "id": "classify_landscape_images",
        "name": "图片横屏分类",
        "category": "图片视频",
        "description": "把横屏图片移动到横屏目录。",
        "risk": "safe",
        "entry": "tools.media_tools:classify_landscape_images",
        "supports_preview": True,
        "schema": [{"name": "input_dir", "label": "输入文件夹", "type": "path", "required": True}],
    },
    {
        "id": "delete_small_videos",
        "name": "删除小视频文件",
        "category": "图片视频",
        "description": "按大小阈值清理小视频，遵循删除策略。",
        "risk": "high",
        "entry": "tools.media_tools:delete_small_videos",
        "supports_preview": True,
        "schema": [
            {"name": "input_dir", "label": "输入文件夹", "type": "path", "required": True},
            {"name": "min_size_mb", "label": "最小大小 MB", "type": "number", "default": 1},
            {"name": "enable_delete", "label": "启用删除", "type": "boolean", "default": False},
        ],
    },
    {
        "id": "delete_low_resolution_videos",
        "name": "视频低分辨率筛选",
        "category": "图片视频",
        "description": "记录低分辨率视频候选项。",
        "risk": "medium",
        "entry": "tools.media_tools:delete_low_resolution_videos",
        "supports_preview": True,
        "schema": [{"name": "input_dir", "label": "输入文件夹", "type": "path", "required": True}],
    },
    {
        "id": "clean_txt_basic",
        "name": "TXT 基础清洗",
        "category": "文本小说",
        "description": "清理广告、乱码符号和重复空行。",
        "risk": "safe",
        "entry": "tools.text_tools:clean_txt_basic",
        "supports_preview": True,
        "schema": [
            {"name": "input_dir", "label": "输入文件夹", "type": "path", "required": True},
            {"name": "output_dir", "label": "输出文件夹", "type": "path", "required": False},
            {"name": "recursive", "label": "递归处理", "type": "boolean", "default": False},
            {"name": "aggressive", "label": "强力清洗", "type": "boolean", "default": False},
        ],
    },
    {
        "id": "clean_txt_ai",
        "name": "AI 输入清洗",
        "category": "文本小说",
        "description": "使用基础清洗作为本地 AI 清洗前置处理。",
        "risk": "safe",
        "entry": "tools.text_tools:clean_txt_ai",
        "supports_preview": True,
        "schema": [
            {"name": "input_dir", "label": "输入文件夹", "type": "path", "required": True},
            {"name": "output_dir", "label": "输出文件夹", "type": "path", "required": False},
        ],
    },
    {
        "id": "split_txt_near_size",
        "name": "按目标字数切分",
        "category": "文本小说",
        "description": "按目标字数附近换行切分 TXT。",
        "risk": "safe",
        "entry": "tools.text_tools:split_txt_near_size",
        "supports_preview": True,
        "schema": [
            {"name": "input_file", "label": "输入 TXT", "type": "path", "required": True},
            {"name": "output_dir", "label": "输出文件夹", "type": "path", "required": False},
            {"name": "target_chars", "label": "目标字数", "type": "number", "default": 3300},
            {"name": "tolerance", "label": "容差", "type": "number", "default": 500},
        ],
    },
    {
        "id": "search_keyword",
        "name": "关键词搜索",
        "category": "文本小说",
        "description": "搜索 TXT 中关键词出现次数。",
        "risk": "safe",
        "entry": "tools.text_tools:search_keyword",
        "supports_preview": True,
        "schema": [
            {"name": "input_dir", "label": "输入文件夹", "type": "path", "required": True},
            {"name": "keyword", "label": "关键词", "type": "text", "required": True},
            {"name": "top_n", "label": "返回数量", "type": "number", "default": 10},
        ],
    },
    {
        "id": "replace_names",
        "name": "人物名替换",
        "category": "文本小说",
        "description": "按 old=>new 映射替换人物名。",
        "risk": "safe",
        "entry": "tools.text_tools:replace_names",
        "supports_preview": True,
        "schema": [
            {"name": "input_file", "label": "输入 TXT", "type": "path", "required": True},
            {"name": "output_file", "label": "输出 TXT", "type": "path", "required": False},
            {"name": "mapping_text", "label": "替换映射", "type": "textarea", "required": True},
        ],
    },
    {
        "id": "split_novel_by_anchor",
        "name": "Anchor 章节切分",
        "category": "文本小说",
        "description": "按章节锚点文本切分小说。",
        "risk": "safe",
        "entry": "tools.text_tools:split_novel_by_anchor",
        "supports_preview": True,
        "schema": [
            {"name": "input_file", "label": "输入 TXT", "type": "path", "required": True},
            {"name": "output_dir", "label": "输出文件夹", "type": "path", "required": False},
            {"name": "anchor_text", "label": "章节锚点", "type": "textarea", "required": False},
        ],
    },
    {
        "id": "group_files",
        "name": "按文件数量分组",
        "category": "文件管理",
        "description": "将文件按数量移动到 group_N 文件夹。",
        "risk": "medium",
        "entry": "tools.file_tools:group_files",
        "supports_preview": True,
        "schema": [
            {"name": "input_dir", "label": "输入文件夹", "type": "path", "required": True},
            {"name": "files_per_group", "label": "每组文件数", "type": "number", "default": 80},
        ],
    },
    {
        "id": "split_large_folder",
        "name": "大文件夹分割",
        "category": "文件管理",
        "description": "按数量分割大文件夹。",
        "risk": "medium",
        "entry": "tools.file_tools:split_large_folder",
        "supports_preview": True,
        "schema": [
            {"name": "input_dir", "label": "输入文件夹", "type": "path", "required": True},
            {"name": "files_per_group", "label": "每组文件数", "type": "number", "default": 3000},
        ],
    },
    {
        "id": "filter_files_by_size",
        "name": "按文件大小筛选",
        "category": "文件管理",
        "description": "按大小复制或移动文件。",
        "risk": "medium",
        "entry": "tools.file_tools:filter_files_by_size",
        "supports_preview": True,
        "schema": [
            {"name": "input_dir", "label": "输入文件夹", "type": "path", "required": True},
            {"name": "min_size_mb", "label": "最小大小 MB", "type": "number", "default": 0},
            {"name": "output_dir", "label": "输出文件夹", "type": "path", "required": False},
        ],
    },
    {
        "id": "batch_change_extension",
        "name": "批量修改后缀名",
        "category": "文件管理",
        "description": "批量把文件改为指定扩展名。",
        "risk": "medium",
        "entry": "tools.file_tools:batch_change_extension",
        "supports_preview": True,
        "schema": [
            {"name": "input_dir", "label": "输入文件夹", "type": "path", "required": True},
            {"name": "extension", "label": "目标后缀", "type": "text", "default": ".rar"},
        ],
    },
    {
        "id": "delete_empty_folders",
        "name": "删除空文件夹",
        "category": "文件管理",
        "description": "清理空文件夹，遵循删除策略。",
        "risk": "high",
        "entry": "tools.file_tools:delete_empty_folders",
        "supports_preview": True,
        "schema": [
            {"name": "input_dir", "label": "输入文件夹", "type": "path", "required": True},
            {"name": "enable_delete", "label": "启用删除", "type": "boolean", "default": False},
        ],
    },
]

FLOWS: list[dict[str, Any]] = [
    {
        "id": "media_clean_standard",
        "name": "图片视频整理标准流程",
        "category": "图片视频流程",
        "description": "重命名、分类、图片降分辨率、可选清理小文件。",
        "risk": "high",
        "entry": "pipelines.media_clean_pipeline:run",
        "supports_preview": True,
        "steps": ["递归重命名", "视频/GIF 分离", "图片横屏分类", "图片降分辨率", "清理小视频文件"],
        "schema": [
            {"name": "input_dir", "label": "输入文件夹", "type": "path", "required": True},
            {"name": "output_dir", "label": "输出文件夹", "type": "path", "required": False},
            {"name": "batch_subfolders", "label": "批量处理子文件夹", "type": "boolean", "default": False},
            {"name": "enable_resize", "label": "启用图片降分辨率", "type": "boolean", "default": True},
            {"name": "enable_delete", "label": "启用删除类步骤", "type": "boolean", "default": False},
        ],
    },
    {
        "id": "txt_clean_split",
        "name": "TXT 清洗 + 3300 字切分流程",
        "category": "文本小说流程",
        "description": "清洗 TXT 后按目标字数切分。",
        "risk": "safe",
        "entry": "pipelines.txt_clean_split_pipeline:run",
        "supports_preview": True,
        "steps": ["TXT 清洗", "按目标字数切分", "生成日志"],
        "schema": [
            {"name": "input_dir", "label": "输入文件夹", "type": "path", "required": True},
            {"name": "output_dir", "label": "输出文件夹", "type": "path", "required": False},
            {"name": "clean_mode", "label": "清洗模式", "type": "select", "default": "basic", "options": ["basic", "ai"]},
            {"name": "target_chars", "label": "目标字数", "type": "number", "default": 3300},
            {"name": "tolerance", "label": "容差", "type": "number", "default": 500},
            {"name": "recursive", "label": "递归处理", "type": "boolean", "default": False},
        ],
    },
    {
        "id": "name_replace",
        "name": "小说人物名替换流程",
        "category": "文本小说流程",
        "description": "按映射替换小说人物名并输出报告。",
        "risk": "safe",
        "entry": "pipelines.name_replace_pipeline:run",
        "supports_preview": True,
        "steps": ["读取 TXT", "解析映射", "替换人物名", "输出报告"],
        "schema": [
            {"name": "input_file", "label": "输入 TXT", "type": "path", "required": True},
            {"name": "output_file", "label": "输出 TXT", "type": "path", "required": False},
            {"name": "mapping_text", "label": "替换映射", "type": "textarea", "required": True},
        ],
    },
    {
        "id": "folder_group",
        "name": "文件夹按数量分组流程",
        "category": "文件整理流程",
        "description": "将文件夹内文件按固定数量分组。",
        "risk": "medium",
        "entry": "pipelines.folder_group_pipeline:run",
        "supports_preview": True,
        "steps": ["读取文件夹", "创建 group_N", "移动文件", "输出统计"],
        "schema": [
            {"name": "input_dir", "label": "输入文件夹", "type": "path", "required": True},
            {"name": "files_per_group", "label": "每组文件数", "type": "number", "default": 80},
        ],
    },
]


def _without_entry(item: dict[str, Any]) -> dict[str, Any]:
    return dict(item)


def list_tools() -> list[dict[str, Any]]:
    return [_without_entry(tool) for tool in TOOLS]


def list_flows() -> list[dict[str, Any]]:
    return [_without_entry(flow) for flow in FLOWS]


def get_tool(tool_id: str) -> dict[str, Any] | None:
    return next((tool for tool in TOOLS if tool["id"] == tool_id), None)


def get_flow(flow_id: str) -> dict[str, Any] | None:
    return next((flow for flow in FLOWS if flow["id"] == flow_id), None)
