"""小工具：剥代码围栏、稳健解析 JSON、Windows 控制台中文输出。"""

import json
import re
import sys


def force_utf8_stdout() -> None:
    """Windows 上 Python 默认按本地编码（GBK）输出，PyCharm 控制台会乱码，统一改成 UTF-8。"""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass


def strip_code_fence(text: str) -> str:
    m = re.search(r"```(?:python|py|sql)?\s*(.*?)```", text, re.S)
    if m:
        return m.group(1).strip()
    return text.strip()


def parse_json(text: str) -> dict:
    m = re.search(r"\{.*\}", text, re.S)
    if not m:
        return {}
    try:
        return json.loads(m.group(0))
    except json.JSONDecodeError:
        return {}
