"""流水线：plan -> code -> execute -> critique -(失败)-> code / -(通过)-> report。

用 LangGraph 组建显式状态机；没装 langgraph 时退化成等价的普通循环，
保证 clone 下来第一次点运行就能跑。

RunConfig 是消融实验的开关：默认全开对应完整四角色。
"""

from dataclasses import dataclass

import config
from ..agents import coder, critic, planner, reporter
from ..runtime import read_schema, run_code
from ..state import AgentState, new_state

MAX_REPAIR_ROUNDS = config.MAX_REPAIR_ROUNDS


@dataclass
class RunConfig:
    use_planner: bool = True
    use_critic: bool = True
    inject_schema: bool = True
    max_rounds: int = MAX_REPAIR_ROUNDS


def _trace_append(state: AgentState, step: dict) -> list[dict]:
    return list(state.get("trace", [])) + [step]


def _nodes(llm, data_path, rc: RunConfig):
    def plan(state: AgentState) -> dict:
        if not rc.use_planner:
            return {"plan": "（已关闭 Planner，直接生成代码）",
                    "trace": _trace_append(state, {"node": "planner", "skipped": True})}
        return planner(llm, state)

    def code(state: AgentState) -> dict:
        if not rc.inject_schema:
            state = {**state, "schema": ""}
        return coder(llm, state)

    def execute(state: AgentState) -> dict:
        ok, out, err = run_code(state.get("code", ""), data_path, config.SANDBOX_TIMEOUT)
        return {
            "result": out if ok else "",
            "error": "" if ok else (err or "执行失败"),
            "trace": _trace_append(state, {
                "node": "executor",
                "ok": ok,
                "stdout": out[:1500],
                "stderr": err[:1500],
            }),
        }

    def critique(state: AgentState) -> dict:
        if not rc.use_critic:
            return {"verdict": True, "reason": "（已关闭 Critic）",
                    "trace": _trace_append(state, {"node": "critic", "skipped": True})}
        return critic(llm, state)

    def report(state: AgentState) -> dict:
        return reporter(llm, state)

    return {"plan": plan, "code": code, "execute": execute, "critique": critique, "report": report}


def _route(state: AgentState) -> str:
    if state.get("verdict"):
        return "report"
    if state.get("rounds", 0) >= state.get("max_rounds", MAX_REPAIR_ROUNDS):
        return "report"
    return "code"


def build_graph(llm, data_path=None, run_config: RunConfig | None = None):
    """返回编译好的 LangGraph 图；未安装 langgraph 则返回 None。"""
    try:
        from langgraph.graph import END, StateGraph
    except ImportError:
        return None

    nodes = _nodes(llm, data_path or config.DATA_PATH, run_config or RunConfig())
    g = StateGraph(AgentState)
    for name, fn in nodes.items():
        g.add_node(name, fn)
    g.set_entry_point("plan")
    g.add_edge("plan", "code")
    g.add_edge("code", "execute")
    g.add_edge("execute", "critique")
    g.add_conditional_edges("critique", _route, {"code": "code", "report": "report"})
    g.add_edge("report", END)
    return g.compile()


def _run_loop(nodes, init: AgentState) -> AgentState:
    state: AgentState = dict(init)
    state.update(nodes["plan"](state))
    while True:
        state.update(nodes["code"](state))
        state.update(nodes["execute"](state))
        state.update(nodes["critique"](state))
        if state.get("verdict") or state.get("rounds", 0) >= state.get("max_rounds", MAX_REPAIR_ROUNDS):
            break
    state.update(nodes["report"](state))
    return state


def run_pipeline(question: str, llm, data_path=None, schema: str | None = None,
                 run_config: RunConfig | None = None) -> AgentState:
    rc = run_config or RunConfig()
    data_path = data_path or config.DATA_PATH
    if schema is None:
        schema = read_schema(data_path)
    init = new_state(question, schema, max_rounds=rc.max_rounds)

    graph = build_graph(llm, data_path, rc)
    if graph is None:
        return _run_loop(_nodes(llm, data_path, rc), init)
    return graph.invoke(init)
