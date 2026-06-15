from __future__ import annotations

from tools import text_tools


def run(params: dict, context: dict) -> dict:
    context["set_current_step"]("读取 TXT", 1)
    context["set_current_step"]("解析映射", 2)
    context["set_current_step"]("替换人物名", 3)
    result = text_tools.replace_names(params, context)
    context["set_current_step"]("输出报告", 4)
    return result
