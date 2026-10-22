"""全局配置。要改行为，改这个文件顶部这几个常量就够了。"""

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent

# ---------- LLM 后端 ----------
# offline = 内置规则基线，不需要 key，CI 和试跑用这个
# deepseek / moonshot / openai / ollama 走 OpenAI 兼容接口
LLM_PROVIDER = "ollama"
LLM_API_KEY = os.getenv("MDA_LLM_API_KEY", "")
LLM_BASE_URL = os.getenv("MDA_LLM_BASE_URL", "")
LLM_MODEL = os.getenv("MDA_LLM_MODEL", "qwen25-3b")
LLM_TEMPERATURE = 0.0
LLM_MAX_TOKENS = 1200
LLM_TIMEOUT = 180

# ---------- 数据 ----------
DATA_PATH = ROOT / "data" / "sample" / "sales.csv"

# ---------- 运行时 ----------
# 沙箱后端：subprocess = 子进程（本机够用）；docker = 真隔离；
# auto = 有 docker 且镜像在就用 docker，否则回退子进程
SANDBOX_BACKEND = os.getenv("MDA_SANDBOX", "auto")
SANDBOX_IMAGE = os.getenv("MDA_SANDBOX_IMAGE", "mdagent-sandbox:latest")
SANDBOX_TIMEOUT = 20
MAX_REPAIR_ROUNDS = 3
TRACE_DIR = ROOT / "runs"

# ---------- 评测 ----------
BENCHMARK_PATH = ROOT / "mdagent" / "eval" / "benchmarks" / "basic.yaml"
EVAL_REPORT_DIR = ROOT / "mdagent" / "eval" / "reports"

# ---------- 入口默认问题（main.py 点运行就用这个） ----------
DEMO_QUESTION = "哪个城市的销售额最高？是多少？"
