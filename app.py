"""Gradio 演示界面。改顶部常量后直接运行本文件：

    DATA_SOURCE  数据源（CSV 文件 / CSV 目录 / 数据库文件）
    SERVER_PORT  本地端口

启动后浏览器打开 http://127.0.0.1:7860
"""

import json
import time

import gradio as gr

import config
from mdagent.graph import RunConfig, run_pipeline
from mdagent.llm import build_backend
from mdagent.runtime import active_backend
from mdagent.utils import force_utf8_stdout

DATA_SOURCE = config.DATA_SOURCE
SERVER_PORT = 7860
MAX_ROUNDS = config.MAX_REPAIR_ROUNDS

EXAMPLES = [
    "哪个城市的销售额最高？是多少？",
    "各类目的总销售额排名，从高到低",
    "6 月相比 5 月的销售额变化了多少？",
    "退货金额最高的三个商品是什么？",
]

CSS = """
.gradio-container {max-width: 1180px !important;}
footer {display: none !important;}
"""

_llm = None


def _get_llm():
    global _llm
    if _llm is None:
        _llm = build_backend()
    return _llm


def _executor_io(trace):
    for step in trace:
        if step.get("node") == "executor":
            return step.get("stdout") or "", step.get("stderr") or ""
    return "", ""


def _trace_text(trace):
    lines = []
    for i, step in enumerate(trace, 1):
        lines.append(f"[{i}] {step.get('node', '?')}")
        for key, val in step.items():
            if key == "node":
                continue
            text = val if isinstance(val, str) else json.dumps(val, ensure_ascii=False)
            lines.append(f"    {key}: {text}")
    return "\n".join(lines) or "(无)"


def answer(question, max_rounds, progress=gr.Progress()):
    question = (question or "").strip()
    if not question:
        raise gr.Error("请输入一个问题")

    progress(0.1, desc="读取表结构")
    started = time.time()
    try:
        state = run_pipeline(
            question, _get_llm(), DATA_SOURCE,
            run_config=RunConfig(max_rounds=int(max_rounds)),
        )
    except Exception as exc:
        raise gr.Error(f"运行失败：{exc}")
    elapsed = time.time() - started

    trace = state.get("trace", [])
    stdout, stderr = _executor_io(trace)

    verdict = "Critic **通过**" if state.get("verdict") else "Critic **未通过**"
    meta = " · ".join([
        f"**{state.get('rounds', 0)}** 轮",
        verdict,
        f"{state.get('prompt_tokens', 0)}+{state.get('completion_tokens', 0)} tokens",
        f"{elapsed:.1f}s",
        f"沙箱 `{active_backend()}`",
    ])
    if state.get("reason"):
        meta += f"\n\n> {state['reason']}"

    return (
        meta,
        state.get("report") or "(没有生成报告)",
        state.get("chart") or None,
        state.get("plan") or "(未生成)",
        state.get("code") or "",
        stdout + (f"\n[stderr]\n{stderr}" if stderr else ""),
        _trace_text(trace),
    )


def build_ui():
    with gr.Blocks(title="mdagent · 多智能体数据分析", css=CSS) as demo:
        gr.Markdown(
            "# mdagent\n"
            "自然语言提数：**Planner** 拆解 → **Coder** 写代码 → 沙箱执行 → "
            "**Critic** 校验 → 失败自动回环修复 → **Reporter** 出结论。"
        )

        with gr.Row():
            with gr.Column(scale=2):
                question = gr.Textbox(
                    label="问题", lines=3,
                    placeholder="例如：哪个城市的销售额最高？是多少？",
                )
                example = gr.Dropdown(choices=EXAMPLES, label="示例问题", value=None)
                rounds = gr.Slider(1, 5, value=MAX_ROUNDS, step=1, label="最大修复轮数")
                submit = gr.Button("运行", variant="primary")

            with gr.Column(scale=3):
                meta = gr.Markdown("等待运行…")
                report = gr.Markdown()
                chart = gr.Image(label="结果图表", type="filepath", height=340)

        with gr.Accordion("Planner 计划", open=False):
            plan = gr.Textbox(lines=6, show_label=False)
        with gr.Accordion("生成的代码", open=False):
            code = gr.Code(language="python", lines=18, show_label=False)
        with gr.Accordion("执行输出", open=False):
            stdout = gr.Textbox(lines=8, show_label=False)
        with gr.Accordion("完整 trace", open=False):
            trace = gr.Textbox(lines=14, show_label=False)

        outputs = [meta, report, chart, plan, code, stdout, trace]
        inputs = [question, rounds]

        example.change(lambda q: q, example, question)
        submit.click(answer, inputs, outputs)
        question.submit(answer, inputs, outputs)

    return demo


def main():
    force_utf8_stdout()
    build_ui().queue().launch(
        server_name="127.0.0.1",
        server_port=SERVER_PORT,
        inbrowser=True,
        show_error=True,
        allowed_paths=[str(config.TRACE_DIR)],
    )


if __name__ == "__main__":
    main()
