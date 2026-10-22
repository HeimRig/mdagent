"""Critic — 验证执行结果是否真的回答了问题，不通过就打回 Coder。"""

from ..state import AgentState
from ..utils import parse_json

SYSTEM = """你是数据分析团队的 Critic。判断下面的执行结果是否真正回答了原始问题。
检查三点：数字/结论是否直接对应问题；是否只是打印了明细而没有结论；结果是否明显异常。
只输出 JSON，不要别的内容：{"pass": true 或 false, "reason": "一句话说明"}"""


def critic(llm, state: AgentState) -> dict:
    result = state.get("result", "")
    if len(result) > 2000:
        result = result[:2000] + "\n...(截断)"

    user = (
        f"问题：{state['question']}\n\n"
        f"代码：\n{state.get('code', '')}\n\n"
        f"执行输出：\n{result}\n\n"
        f"执行报错：{state.get('error', '') or '无'}"
    )
    reply = llm.chat(SYSTEM, user, role="critic")
    data = parse_json(reply.text)

    verdict = bool(data.get("pass", True))
    reason = data.get("reason", "")
    if state.get("error"):
        verdict = False
        reason = reason or "执行失败"

    trace = list(state.get("trace", []))
    trace.append({"node": "critic", "verdict": verdict, "reason": reason})
    return {
        "verdict": verdict,
        "reason": reason,
        "trace": trace,
        "prompt_tokens": state.get("prompt_tokens", 0) + reply.prompt_tokens,
        "completion_tokens": state.get("completion_tokens", 0) + reply.completion_tokens,
    }
