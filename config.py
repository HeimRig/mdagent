"""全局配置。要改行为，改这个文件顶部这几个常量就够了。"""

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def _dotenv() -> dict[str, str]:
    path = ROOT / ".env"
    if not path.exists():
        return {}
    data: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        data[key.strip()] = value.strip().strip('"').strip("'")
    return data


_ENV = _dotenv()

# ---------- LLM 后端 ----------
# offline = 内置规则基线，不需要 key，CI 和试跑用这个
# deepseek / moonshot / openai / ollama 走 OpenAI 兼容接口
LLM_PROVIDER = "deepseek"
LLM_API_KEY = os.getenv("MDA_LLM_API_KEY") or _ENV.get("MDA_LLM_API_KEY", "")
LLM_BASE_URL = os.getenv("MDA_LLM_BASE_URL") or _ENV.get("MDA_LLM_BASE_URL", "")
LLM_MODEL = os.getenv("MDA_LLM_MODEL") or _ENV.get("MDA_LLM_MODEL", "")
LLM_TEMPERATURE = 0.0
LLM_MAX_TOKENS = 1200
LLM_TIMEOUT = 180

# ---------- 数据 ----------
# 可以是单个 CSV、装着多个 CSV 的目录、或者 .duckdb / .sqlite 文件
DATA_SOURCE = os.getenv("MDA_DATA_SOURCE", str(ROOT / "data" / "sample"))

# ---------- 运行时 ----------
# 沙箱后端：subprocess = 子进程（本机够用）；docker = 真隔离；
# auto = 有 docker 且镜像在就用 docker，否则回退子进程
SANDBOX_BACKEND = os.getenv("MDA_SANDBOX", "auto")
SANDBOX_IMAGE = os.getenv("MDA_SANDBOX_IMAGE", "mdagent-sandbox:latest")
SANDBOX_TIMEOUT = 20
MAX_REPAIR_ROUNDS = 3
TRACE_DIR = ROOT / "runs"

# ---------- 出图 ----------
# 结果表格满足「一个类别列 + 一个数值列」时自动画图
ENABLE_CHART = True
FIGURE_DIR = TRACE_DIR / "figures"

# ---------- 评测 ----------
BENCHMARK_PATH = ROOT / "mdagent" / "eval" / "benchmarks" / "basic.yaml"
EVAL_REPORT_DIR = ROOT / "mdagent" / "eval" / "reports"

# ---------- 入口默认问题（main.py 点运行就用这个） ----------
DEMO_QUESTION = "哪个城市的销售额最高？是多少？"
