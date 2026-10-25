"""入口。改 config.py 顶部的常量，然后直接运行本文件即可。

默认跑 config.DEMO_QUESTION，并把完整 trace 存到 runs/ 下。
"""

import json
from datetime import datetime

import config
from mdagent.graph import run_pipeline
from mdagent.llm import build_backend
from mdagent.utils import force_utf8_stdout


def main() -> None:
    force_utf8_stdout()
    llm = build_backend()
    state = run_pipeline(config.DEMO_QUESTION, llm, config.DATA_PATH)

    line = "=" * 64
    print(line)
    print("问 题:", state["question"])
    print("后 端:", llm.name)
    print(line)
    print(state.get("report") or "(没有生成报告)")
    print(line)
    if state.get("chart"):
        print("图表 ->", state["chart"])
    print(
        f"轮数 {state.get('rounds')} | Critic 通过 {state.get('verdict')} "
        f"| token {state.get('prompt_tokens')}+{state.get('completion_tokens')}"
    )

    config.TRACE_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    out = config.TRACE_DIR / f"trace-{stamp}.json"
    out.write_text(json.dumps(state, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    print("trace ->", out)


if __name__ == "__main__":
    main()
