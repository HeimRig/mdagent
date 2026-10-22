"""mdagent — 多智能体数据分析 Agent。"""

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

__version__ = "0.1.0"
