from mdagent.graph import RunConfig, run_pipeline
from mdagent.llm import build_backend
from mdagent.eval.ablation import PROFILES


def _run(question, rc):
    return run_pipeline(question, build_backend("offline"), run_config=rc)


def test_no_critic_short_circuits_verdict():
    state = _run("哪个城市的销售额最高？是多少？", RunConfig(use_critic=False))
    steps = [s for s in state["trace"] if s["node"] == "critic"]
    assert steps and steps[-1].get("skipped") is True
    assert state["verdict"] is True
    assert "杭州" in state["result"]


def test_no_planner_marks_skipped():
    state = _run("一共有多少笔订单？", RunConfig(use_planner=False))
    steps = [s for s in state["trace"] if s["node"] == "planner"]
    assert steps and steps[-1].get("skipped") is True


def test_max_rounds_caps_repair():
    state = _run("平均每个订单的金额是多少？", RunConfig(max_rounds=1))
    assert state["rounds"] == 1


def test_no_schema_still_runs():
    state = _run("所有订单的总销售额是多少？", RunConfig(inject_schema=False))
    assert state["result"]


def test_profiles_have_unique_names():
    names = [name for name, _, _ in PROFILES]
    assert names[0] == "full"
    assert len(names) == len(set(names))
