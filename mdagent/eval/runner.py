"""跑 benchmark，输出控制台表格 + markdown 报告 + json 明细。

    python -m mdagent.eval.runner
    python -m mdagent.eval.runner --provider deepseek
"""

import argparse
import json
import time
from pathlib import Path

import yaml

import config
from ..graph import run_pipeline
from ..llm import build_backend
from ..runtime import active_backend
from ..utils import force_utf8_stdout
from .metrics import evaluate, summarize


def load_benchmark(path: Path | None = None) -> list[dict]:
    path = Path(path or config.BENCHMARK_PATH)
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def run_benchmark(provider: str | None = None, limit: int | None = None) -> dict:
    llm = build_backend(provider)
    items = load_benchmark()
    if limit:
        items = items[:limit]

    records = []
    for item in items:
        llm.reset()
        t0 = time.perf_counter()
        try:
            state = run_pipeline(item["question"], llm)
        except Exception as exc:  # 单题崩了不拖垮整轮评测
            state = {"result": "", "error": str(exc), "rounds": 0, "verdict": False, "trace": []}
        latency = round(time.perf_counter() - t0, 2)

        rec = {"id": item["id"], "question": item["question"], "tag": item.get("tag", ""),
               "expect": item.get("expect", ""), "latency_s": latency,
               "prompt_tokens": state.get("prompt_tokens", 0),
               "completion_tokens": state.get("completion_tokens", 0),
               "result": (state.get("result") or "").strip()[:200],
               "error": (state.get("error") or "")[:200]}
        rec.update(evaluate(item.get("expect", ""), state))
        records.append(rec)

    summary = summarize(records)
    summary["provider"] = llm.name
    return {"summary": summary, "records": records}


def write_reports(run: dict) -> Path:
    config.EVAL_REPORT_DIR.mkdir(parents=True, exist_ok=True)
    md = config.EVAL_REPORT_DIR / "report.md"
    (config.EVAL_REPORT_DIR / "report.json").write_text(
        json.dumps(run, ensure_ascii=False, indent=2, default=str), encoding="utf-8")

    s = run["summary"]
    lines = [
        "# Benchmark 报告",
        "",
        f"- 后端: `{s['provider']}`",
        f"- 沙箱: `{active_backend()}`",
        f"- 题量: {s['total']}",
        f"- 答案准确率: **{s['answer_accuracy']:.2%}**",
        f"- 执行成功率: {s['exec_success_rate']:.2%}",
        f"- Critic 通过率: {s['critic_pass_rate']:.2%}",
        f"- 平均自愈轮数: {s['avg_rounds']}",
        f"- 平均延迟: {s['avg_latency_s']}s",
        f"- 平均 token: {s['avg_tokens']}",
        "",
        "| id | 题型 | 问题 | 期望 | 命中 | 执行 | 轮数 | 延迟(s) |",
        "|----|------|------|------|------|------|------|---------|",
    ]
    for r in run["records"]:
        lines.append(
            f"| {r['id']} | {r.get('tag', '')} | {r['question']} | `{r.get('expect', '')}` "
            f"| {'Y' if r['answer_ok'] else 'N'} "
            f"| {'Y' if r['exec_ok'] else 'N'} | {r['rounds']} | {r['latency_s']} |"
        )

    tags = s.get("by_tag") or {}
    if tags:
        lines += ["", "## 分题型准确率", "", "| 题型 | 题数 | 准确率 | 执行成功率 |",
                  "|------|------|--------|-----------|"]
        for tag, v in tags.items():
            lines.append(f"| {tag} | {v['total']} | {v['answer_accuracy']:.2%} "
                         f"| {v['exec_success_rate']:.2%} |")

    md.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return md


def main() -> None:
    force_utf8_stdout()
    ap = argparse.ArgumentParser()
    ap.add_argument("--provider", default=None, help="offline / deepseek / moonshot / openai / ollama")
    ap.add_argument("--limit", type=int, default=None)
    args = ap.parse_args()

    run = run_benchmark(args.provider, args.limit)
    print(f"backend = {run['summary']['provider']}")
    for k, v in run["summary"].items():
        if k not in ("provider", "by_tag"):
            print(f"  {k:20s} {v}")
    for tag, v in (run["summary"].get("by_tag") or {}).items():
        print(f"  [{tag}] n={v['total']} acc={v['answer_accuracy']:.2%} exec={v['exec_success_rate']:.2%}")
    print("report ->", write_reports(run))


if __name__ == "__main__":
    main()
