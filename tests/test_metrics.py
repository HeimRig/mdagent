from mdagent.eval.metrics import evaluate, summarize


def _state(result):
    return {"result": result, "error": "", "rounds": 1, "verdict": True}


def test_exact_substring_hit():
    assert evaluate("8450.30", _state("total\n8450.30"))["answer_ok"] is True


def test_rounding_variance_still_hits():
    assert evaluate("49120.80", _state("total\n49120.8"))["answer_ok"] is True
    assert evaluate("49120.80", _state("total\n49121"))["answer_ok"] is True


def test_close_but_wrong_number_misses():
    assert evaluate("17.92", _state("pct\n17.20"))["answer_ok"] is False


def test_non_numeric_expectation_uses_substring():
    assert evaluate("杭州", _state("city\n杭州"))["answer_ok"] is True
    assert evaluate("杭州", _state("city\n上海"))["answer_ok"] is False


def test_empty_result_never_hits():
    assert evaluate("240", _state(""))["answer_ok"] is False


def test_by_tag_groups_accuracy():
    records = [
        {"tag": "top1", "answer_ok": True, "exec_ok": True, "rounds": 1, "verified": True,
         "latency_s": 1.0, "prompt_tokens": 1, "completion_tokens": 1},
        {"tag": "top1", "answer_ok": False, "exec_ok": True, "rounds": 2, "verified": True,
         "latency_s": 1.0, "prompt_tokens": 1, "completion_tokens": 1},
        {"tag": "ratio", "answer_ok": True, "exec_ok": True, "rounds": 1, "verified": True,
         "latency_s": 1.0, "prompt_tokens": 1, "completion_tokens": 1},
    ]
    stats = summarize(records)
    assert stats["by_tag"]["top1"]["answer_accuracy"] == 0.5
    assert stats["by_tag"]["ratio"]["answer_accuracy"] == 1.0
