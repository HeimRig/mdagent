"""评测指标：答案是否命中、执行是否成功、自愈轮数。"""

import re

_STRIP = re.compile(r"[\s,，、¥$元]")
_NUM = re.compile(r"-?\d[\d,]*(?:\.\d+)?")


def normalize(text: str) -> str:
    return _STRIP.sub("", str(text or "")).lower()


def _numbers(text: str) -> list[float]:
    out = []
    for m in _NUM.finditer(str(text or "")):
        try:
            out.append(float(m.group(0).replace(",", "")))
        except ValueError:
            pass
    return out


def _numeric_hit(expected: str, result: str) -> bool:
    """子串匹配对四舍五入太脆（49120.8 vs 49120.80），数值再比一次。"""
    try:
        exp = float(str(expected).replace(",", "").strip())
    except ValueError:
        return False
    tol = max(0.02, abs(exp) * 1e-5)
    return any(abs(n - exp) <= tol for n in _numbers(result))


def evaluate(expected: str, state: dict) -> dict:
    """expected 是期望答案：优先子串匹配，数字再走一次容差比较。"""
    result = state.get("result", "") or ""
    hit = bool(expected) and (
        normalize(expected) in normalize(result) or _numeric_hit(expected, result)
    )
    return {
        "answer_ok": hit,
        "exec_ok": bool(result) and not state.get("error"),
        "rounds": state.get("rounds", 0),
        "verified": bool(state.get("verdict")),
    }


def _rate(records: list[dict], key: str) -> float:
    return round(sum(bool(r[key]) for r in records) / len(records), 4)


def by_tag(records: list[dict]) -> dict:
    groups: dict[str, list[dict]] = {}
    for r in records:
        groups.setdefault(r.get("tag") or "untagged", []).append(r)
    return {
        tag: {
            "total": len(rs),
            "answer_accuracy": _rate(rs, "answer_ok"),
            "exec_success_rate": _rate(rs, "exec_ok"),
        }
        for tag, rs in sorted(groups.items())
    }


def summarize(records: list[dict]) -> dict:
    n = len(records) or 1
    return {
        "total": len(records),
        "exec_success_rate": round(sum(r["exec_ok"] for r in records) / n, 4),
        "answer_accuracy": round(sum(r["answer_ok"] for r in records) / n, 4),
        "critic_pass_rate": round(sum(r["verified"] for r in records) / n, 4),
        "avg_rounds": round(sum(r["rounds"] for r in records) / n, 2),
        "avg_latency_s": round(sum(r["latency_s"] for r in records) / n, 2),
        "avg_tokens": round(sum(r["prompt_tokens"] + r["completion_tokens"] for r in records) / n, 1),
        "by_tag": by_tag(records),
    }
