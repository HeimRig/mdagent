"""连跑 N 次 benchmark，检查结果是否可复现。

    python -m mdagent.eval.stability --provider deepseek --runs 3
"""

import argparse
import json

import config
from ..utils import force_utf8_stdout
from .runner import run_benchmark


def main() -> None:
    force_utf8_stdout()
    ap = argparse.ArgumentParser()
    ap.add_argument("--provider", default="deepseek")
    ap.add_argument("--runs", type=int, default=3)
    ap.add_argument("--limit", type=int, default=None)
    args = ap.parse_args()

    out_dir = config.EVAL_REPORT_DIR
    out_dir.mkdir(parents=True, exist_ok=True)

    runs = []
    for i in range(args.runs):
        run = run_benchmark(args.provider, args.limit)
        runs.append(run)
        s = run["summary"]
        print(f"[run {i + 1}] acc={s['answer_accuracy']:.4f} "
              f"exec={s['exec_success_rate']:.4f} critic={s['critic_pass_rate']:.4f} "
              f"rounds={s['avg_rounds']} latency={s['avg_latency_s']} "
              f"tokens={s['avg_tokens']}", flush=True)
        (out_dir / f"report-run{i + 1}.json").write_text(
            json.dumps(run, ensure_ascii=False, indent=2, default=str), encoding="utf-8")

    accs = [r["summary"]["answer_accuracy"] for r in runs]
    print()
    print("准确率 :", [f"{a:.2%}" for a in accs])
    print("极差   :", f"{(max(accs) - min(accs)) * 100:.2f} pt")

    print("\n逐题翻转")
    flips = 0
    for idx, rec in enumerate(runs[0]["records"]):
        hits = [runs[k]["records"][idx]["answer_ok"] for k in range(len(runs))]
        if len(set(hits)) > 1:
            flips += 1
            print(f"  {rec['id']} ({rec.get('tag')}): {hits}  {rec['question']}")
    if not flips:
        print("  无，各次完全一致")

    print("\n稳定错题")
    misses = [rec for idx, rec in enumerate(runs[0]["records"])
              if not any(runs[k]["records"][idx]["answer_ok"] for k in range(len(runs)))]
    for rec in misses:
        print(f"  {rec['id']} ({rec.get('tag')}): {rec['question']}")
    if not misses:
        print("  无")


if __name__ == "__main__":
    main()
