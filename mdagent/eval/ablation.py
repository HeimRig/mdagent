"""消融实验：逐项关掉流水线组件，对比指标，产出 README 里的对比表。

    python -m mdagent.eval.ablation
    python -m mdagent.eval.ablation --provider deepseek
"""

import argparse
import json
import time
from pathlib import Path

import config
from ..graph import RunConfig, run_pipeline
from ..llm import build_backend
from ..runtime import active_backend
from ..utils import force_utf8_stdout
from .metrics import evaluate, summarize
from .runner import load_benchmark

PROFILES: list[tuple[str, str, RunConfig]] = [
    ("full", "完整四角色（Planner + Coder + Critic + 自愈）", RunConfig()),
    ("no_critic", "去掉 Critic 校验", RunConfig(use_critic=False)),
    ("no_repair", "只生成一次代码，不自愈", RunConfig(max_rounds=1)),
    ("no_schema", "不注入表结构", RunConfig(inject_schema=False)),
    ("single_agent", "单 agent（无 Planner、无 Critic）",
     RunConfig(use_planner=False, use_critic=False, max_rounds=1)),
]


def run_profile(name: str, rc: RunConfig, provider: str | None, items: list[dict]) -> dict:
    llm = build_backend(provider)
    records = []
    for item in items:
        llm.reset()
        t0 = time.perf_counter()
        try:
            state = run_pipeline(item["question"], llm, run_config=rc)
        except Exception as exc:
            state = {"result": "", "error": str(exc), "rounds": 0, "verdict": False}
        latency = round(time.perf_counter() - t0, 2)

        rec = {
            "id": item["id"],
            "tag": item.get("tag", ""),
            "latency_s": latency,
            "prompt_tokens": state.get("prompt_tokens", 0),
            "completion_tokens": state.get("completion_tokens", 0),
        }
        rec.update(evaluate(item.get("expect", ""), state))
        records.append(rec)

    stats = summarize(records)
    stats["profile"] = name
    stats["provider"] = llm.name
    stats["records"] = records
    return stats


def write_report(rows: list[dict], provider: str) -> Path:
    config.EVAL_REPORT_DIR.mkdir(parents=True, exist_ok=True)
    (config.EVAL_REPORT_DIR / "ablation.json").write_text(
        json.dumps(rows, ensure_ascii=False, indent=2, default=str), encoding="utf-8")

    lines = [
        "# 消融实验",
        "",
        f"- 后端: `{provider}`",
        f"- 沙箱: `{active_backend()}`",
        f"- 题量: {rows[0]['total'] if rows else 0}",
        "",
        "| 配置 | 说明 | 答案准确率 | 执行成功率 | 平均自愈轮数 | 平均延迟(s) |",
        "|------|------|-----------|-----------|-------------|------------|",
    ]
    for r in rows:
        lines.append(
            f"| `{r['profile']}` | {r['desc']} | {r['answer_accuracy']:.2%} "
            f"| {r['exec_success_rate']:.2%} | {r['avg_rounds']} | {r['avg_latency_s']} |"
        )
    lines += ["", "逐题明细见 `ablation.json`。"]
    if provider == "offline":
        lines += [
            "",
            "> 离线后端是「关键词 → SQL」的规则映射，不读表结构、也不做二次判断，",
            "> 所以各配置数值相同属于预期。组件开关的真实影响要用真模型跑：",
            "> `python -m mdagent.eval.ablation --provider deepseek`",
        ]
    md = config.EVAL_REPORT_DIR / "ablation.md"
    md.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return md


def main() -> None:
    force_utf8_stdout()
    ap = argparse.ArgumentParser()
    ap.add_argument("--provider", default=None, help="offline / deepseek / moonshot / openai / ollama")
    ap.add_argument("--limit", type=int, default=None)
    args = ap.parse_args()

    items = load_benchmark()
    if args.limit:
        items = items[:args.limit]

    rows = []
    for name, desc, rc in PROFILES:
        stats = run_profile(name, rc, args.provider, items)
        rows.append({"name": name, "desc": desc, **stats})
        print(f"{name:14s} acc={stats['answer_accuracy']:.2%} "
              f"exec={stats['exec_success_rate']:.2%} rounds={stats['avg_rounds']}")

    print("report ->", write_report(rows, rows[0]["provider"] if rows else "unknown"))


if __name__ == "__main__":
    main()
