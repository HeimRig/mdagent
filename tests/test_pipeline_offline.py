from mdagent.graph import run_pipeline
from mdagent.llm import build_backend
from mdagent.eval.metrics import evaluate, summarize


def _run(question):
    llm = build_backend("offline")
    return run_pipeline(question, llm)


def test_pipeline_answers_top_city():
    state = _run("哪个城市的销售额最高？是多少？")
    assert state["result"]
    assert state["verdict"] is True
    assert "杭州" in state["result"]


def test_pipeline_report_is_markdown():
    state = _run("一共有多少笔订单？")
    assert "结论" in state["report"]


def test_pipeline_trace_records_every_node():
    llm = build_backend("offline")
    state = run_pipeline("平均每个订单的金额是多少？", llm)
    nodes = [step["node"] for step in state["trace"]]
    assert nodes[0] == "planner"
    assert "executor" in nodes
    assert "critic" in nodes
    assert "reporter" in nodes
    assert nodes[-1] in ("reporter", "chart")


def test_metrics_flag_missing_answer():
    llm = build_backend("offline")
    state = run_pipeline("平均每个订单的金额是多少？", llm)
    assert evaluate("94.17", state)["answer_ok"] is False


def test_summarize_shape():
    stats = summarize([
        {"answer_ok": True, "exec_ok": True, "rounds": 1, "verified": True,
         "latency_s": 0.5, "prompt_tokens": 10, "completion_tokens": 5},
    ])
    assert stats["answer_accuracy"] == 1.0
    assert stats["avg_rounds"] == 1
