"""图状态定义。所有节点读写同一个 dict。"""

from typing import Any, TypedDict


class AgentState(TypedDict, total=False):
    question: str
    schema: str
    plan: str
    code: str
    result: str
    error: str
    verdict: bool
    reason: str
    rounds: int
    report: str
    chart: str
    trace: list[dict[str, Any]]
    max_rounds: int
    prompt_tokens: int
    completion_tokens: int


def new_state(question: str, schema: str, max_rounds: int = 3) -> AgentState:
    return AgentState(
        question=question,
        schema=schema,
        plan="",
        code="",
        result="",
        error="",
        verdict=False,
        reason="",
        rounds=0,
        report="",
        chart="",
        trace=[],
        max_rounds=max_rounds,
        prompt_tokens=0,
        completion_tokens=0,
    )


def log(state: AgentState, node: str, **detail: Any) -> None:
    state.setdefault("trace", []).append({"node": node, **detail})
