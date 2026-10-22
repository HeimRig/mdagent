"""离线规则基线。不需要 API key，用于 CI 和本地试跑。

它按关键词把问题映射成 SQL，不调用任何模型。所以它只能算一个
"能不能跑通" 的对照组，真实准确率请用真模型跑同一套 benchmark 对比。
"""

import json

from .base import LLMBackend, LLMReply

_RULES: list[tuple[tuple[str, ...], str]] = [
    (("最高", "城市"), "SELECT city, ROUND(SUM(amount),2) AS total FROM sales GROUP BY city ORDER BY total DESC LIMIT 1"),
    (("城市",), "SELECT city, ROUND(SUM(amount),2) AS total FROM sales GROUP BY city ORDER BY total DESC"),
    (("分类",), "SELECT category, ROUND(SUM(amount),2) AS total FROM sales GROUP BY category ORDER BY total DESC"),
    (("品类",), "SELECT category, ROUND(SUM(amount),2) AS total FROM sales GROUP BY category ORDER BY total DESC"),
    (("多少笔",), "SELECT COUNT(*) AS orders FROM sales"),
    (("多少条",), "SELECT COUNT(*) AS orders FROM sales"),
    (("订单数",), "SELECT COUNT(*) AS orders FROM sales"),
    (("平均", "单价"), "SELECT ROUND(AVG(unit_price),2) AS avg_price FROM sales"),
    (("个月",), "SELECT strftime(date, '%Y-%m') AS month, ROUND(SUM(amount),2) AS total FROM sales GROUP BY month ORDER BY month"),
    (("按月",), "SELECT strftime(date, '%Y-%m') AS month, ROUND(SUM(amount),2) AS total FROM sales GROUP BY month ORDER BY month"),
    (("月度",), "SELECT strftime(date, '%Y-%m') AS month, ROUND(SUM(amount),2) AS total FROM sales GROUP BY month ORDER BY month"),
    (("总销售额",), "SELECT ROUND(SUM(amount),2) AS total FROM sales"),
    (("总额",), "SELECT ROUND(SUM(amount),2) AS total FROM sales"),
    (("最高", "产品"), "SELECT product, ROUND(SUM(amount),2) AS total FROM sales GROUP BY product ORDER BY total DESC LIMIT 1"),
]

_DEFAULT_SQL = "SELECT * FROM sales LIMIT 5"

_TEMPLATE = """import os
import duckdb

DATA = os.environ["MDA_DATA"]
con = duckdb.connect()
con.execute("CREATE VIEW sales AS SELECT * FROM read_csv_auto('" + DATA + "')")
print(con.execute(__SQL__).fetchdf().to_string(index=False))
"""


def _pick_sql(question: str) -> str:
    for keys, sql in _RULES:
        if all(k in question for k in keys):
            return sql
    return _DEFAULT_SQL


class OfflineBackend(LLMBackend):
    def __init__(self) -> None:
        super().__init__(name="offline")

    def chat(self, system: str, user: str, **kwargs) -> LLMReply:
        role = kwargs.get("role", "")
        if role == "planner":
            text = "1. 读取数据表 sales\n2. 按问题聚合计算\n3. 打印结果"
        elif role == "coder":
            text = "```python\n" + _TEMPLATE.replace("__SQL__", repr(_pick_sql(user))) + "```"
        elif role == "critic":
            text = json.dumps({"pass": True, "reason": "离线基线：执行成功即视为通过"}, ensure_ascii=False)
        else:
            text = f"## 结论\n\n基于离线基线执行结果：\n\n```\n{user[-400:]}\n```\n"
        return self._account(LLMReply(text=text))
