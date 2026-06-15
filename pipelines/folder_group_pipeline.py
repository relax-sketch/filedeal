from __future__ import annotations

from tools import file_tools


def run(params: dict, context: dict) -> dict:
    context["set_current_step"]("读取文件夹", 1)
    context["set_current_step"]("创建 group_N", 2)
    context["set_current_step"]("移动文件", 3)
    result = file_tools.group_files(params, context)
    context["set_current_step"]("输出统计", 4)
    return result
