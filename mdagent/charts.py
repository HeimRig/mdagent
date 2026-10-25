"""把执行结果里的表格画成一张图。数据形状不合适就返回 None，不硬画。"""

import re
from datetime import datetime
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

import config

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False

MAX_ROWS = 20
BAR_COLOR = "#4C78A8"


def _split_blocks(text: str) -> list[list[list[str]]]:
    blocks: list[list[list[str]]] = []
    current: list[list[str]] = []
    for line in text.splitlines():
        if not line.strip():
            continue
        parts = [p for p in re.split(r"\s{2,}", line.strip()) if p]
        if len(parts) >= 2 and not any(ch in line for ch in "{}[]=<>"):
            current.append(parts)
        else:
            if len(current) >= 2:
                blocks.append(current)
            current = []
    if len(current) >= 2:
        blocks.append(current)
    return blocks


def parse_table(text: str) -> pd.DataFrame | None:
    """从 stdout 里捞等宽表格（pandas 的 to_string 输出）。"""
    blocks = _split_blocks(text or "")
    if not blocks:
        return None

    block = max(blocks, key=len)
    width = max(len(row) for row in block)
    rows = [row for row in block if len(row) == width][-MAX_ROWS - 1:]
    if len(rows) < 2:
        return None

    df = pd.DataFrame(rows[1:], columns=rows[0])
    for col in df.columns:
        numeric = pd.to_numeric(df[col], errors="coerce")
        if numeric.notna().all():
            df[col] = numeric
    return df if not df.empty else None


def _pick_axes(df: pd.DataFrame) -> tuple[str | None, str | None]:
    numeric = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
    if not numeric:
        return None, None
    rest = [c for c in df.columns if c not in numeric]
    category = min(rest, key=lambda c: df[c].nunique()) if rest else None
    value = max(numeric, key=lambda c: df[c].abs().sum())
    return category, value


def build_chart(result_text: str, question: str = "", out_dir: Path | None = None) -> Path | None:
    if not getattr(config, "ENABLE_CHART", True):
        return None

    df = parse_table(result_text)
    if df is None or len(df) < 2:
        return None

    category, value = _pick_axes(df)
    if value is None:
        return None

    labels = [str(v) for v in df[category]] if category else [str(i + 1) for i in range(len(df))]
    values = df[value].fillna(0).tolist()
    if not any(values):
        return None

    n = len(df)
    horizontal = n > 6 or max(len(s) for s in labels) > 8

    if horizontal:
        order = sorted(range(n), key=lambda i: values[i])
        labels = [labels[i] for i in order]
        values = [values[i] for i in order]
        fig, ax = plt.subplots(figsize=(7.8, 0.36 * n + 1.4))
        ax.barh(labels, values, color=BAR_COLOR, height=0.62)
        ax.grid(axis="x", alpha=0.25)
        ax.set_axisbelow(True)
    else:
        fig, ax = plt.subplots(figsize=(7.4, 4.2))
        ax.bar(labels, values, color=BAR_COLOR, width=0.62)
        ax.grid(axis="y", alpha=0.25)
        ax.set_axisbelow(True)

    for side in ("top", "right"):
        ax.spines[side].set_visible(False)

    title = (question or "").strip().replace("\n", " ")
    ax.set_title(title[:46] + ("…" if len(title) > 46 else ""), fontsize=12, pad=12)

    if horizontal:
        ax.set_xlabel(value)
    else:
        ax.set_ylabel(value)

    out_dir = Path(out_dir or config.FIGURE_DIR)
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    path = out_dir / f"chart-{stamp}.png"

    fig.tight_layout()
    fig.savefig(path, dpi=140, bbox_inches="tight")
    plt.close(fig)
    return path
