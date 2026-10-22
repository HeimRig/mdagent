"""Planner — 把问题拆成分析步骤，决定用 SQL 还是 Pandas。"""

from ..state import AgentState

SYSTEM = """你是数据分析团队的 Planner。
给定一个业务问题和数据表结构，把问题拆成 2-4 个可执行的分析步骤。
只输出步骤列表，每行一句。不要写代码，不要解释原理。"""


def planner(llm, state: AgentState) -> dict:
    user = f"问题：{state['question']}\n\n表结构：\n{state['schema']}"
    reply = llm.chat(SYSTEM, user, role="planner")

    trace = list(state.get("trace", []))
    trace.append({"node": "planner", "plan": reply.text})
    return {
        "plan": reply.text,
        "trace": trace,
        "prompt_tokens": state.get("prompt_tokens", 0) + reply.prompt_tokens,
        "completion_tokens": state.get("completion_tokens", 0) + reply.completion_tokens,
    }
