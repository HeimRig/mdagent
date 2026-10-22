"""Reporter — 把结论写成 markdown 报告。"""

from ..state import AgentState

SYSTEM = """你是数据分析团队的 Reporter。把分析结果写成一段简短的 markdown 报告。
结构固定为两部分：`## 结论` 和 `## 依据`。
只能使用给定输出里的数字，严禁编造。若未得到有效结果，直接说明失败原因。"""


def reporter(llm, state: AgentState) -> dict:
    result = state.get("result", "")
    if not result.strip():
        reason = state.get("reason") or state.get("error") or "代码执行未产出任何结果"
        text = (
            "## 结论\n\n"
            "未得到可靠结果，不做推测。\n\n"
            "## 依据\n\n"
            f"- 已尝试轮数：{state.get('rounds', 0)}\n"
            f"- 失败原因：{reason}\n"
        )
        trace = list(state.get("trace", []))
        trace.append({"node": "reporter", "short_circuit": True})
        return {"report": text, "trace": trace}

    if len(result) > 2000:
        result = result[:2000] + "\n...(截断)"

    user = (
        f"问题：{state['question']}\n\n"
        f"执行输出：\n{result or '（无）'}\n\n"
        f"执行报错：{state.get('error', '') or '无'}\n\n"
        f"Critic 意见：{state.get('reason', '') or '无'}\n\n"
        f"已尝试轮数：{state.get('rounds', 0)}"
    )
    reply = llm.chat(SYSTEM, user, role="reporter")

    trace = list(state.get("trace", []))
    trace.append({"node": "reporter"})
    return {
        "report": reply.text,
        "trace": trace,
        "prompt_tokens": state.get("prompt_tokens", 0) + reply.prompt_tokens,
        "completion_tokens": state.get("completion_tokens", 0) + reply.completion_tokens,
    }
