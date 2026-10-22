from collections import Counter

from mdagent.eval.runner import load_benchmark


def test_benchmark_is_well_formed():
    items = load_benchmark()
    assert len(items) >= 20
    ids = [i["id"] for i in items]
    assert len(ids) == len(set(ids)), "题目 id 重复"
    for item in items:
        assert item["question"].strip()
        assert item["tag"].strip()
        assert item["expect"].strip(), f"{item['id']} 缺少期望答案"
        assert item["gold_sql"].strip(), f"{item['id']} 缺少 reference SQL"


def test_benchmark_covers_multiple_types():
    tags = Counter(i["tag"] for i in load_benchmark())
    for tag in ("top1", "aggregate", "groupby", "filter", "multistep", "ratio"):
        assert tags[tag] >= 1, f"缺少题型 {tag}"
