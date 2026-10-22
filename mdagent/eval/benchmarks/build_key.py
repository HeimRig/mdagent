"""生成 benchmark 答案键：每题配一条 reference SQL，expect 由 SQL 实算。

    python -m mdagent.eval.benchmarks.build_key

答案不从模型输出里抄，也不手敲，改数据后重跑即可同步。
"""

import sys
from pathlib import Path

import duckdb
import yaml

DATA = Path(__file__).resolve().parents[3] / "data" / "sample" / "sales.csv"
OUT = Path(__file__).parent / "basic.yaml"

QUESTS: list[tuple[str, str, str, str]] = [
    ("q1", "哪个城市的销售额最高？是多少？", "top1",
     "SELECT ROUND(SUM(amount),2) AS v FROM sales GROUP BY city ORDER BY v DESC LIMIT 1"),
    ("q2", "一共有多少笔订单？", "count", "SELECT COUNT(*) AS v FROM sales"),
    ("q3", "所有订单的总销售额是多少？", "aggregate",
     "SELECT ROUND(SUM(amount),2) AS v FROM sales"),
    ("q4", "销售额最高的商品分类，其销售额是多少？", "groupby",
     "SELECT ROUND(SUM(amount),2) AS v FROM sales GROUP BY category ORDER BY v DESC LIMIT 1"),
    ("q5", "销售额最高的那个月，销售额是多少？", "timeseries",
     "SELECT ROUND(SUM(amount),2) AS v FROM sales "
     "GROUP BY strftime(date,'%Y-%m') ORDER BY v DESC LIMIT 1"),
    ("q6", "平均每个订单的金额是多少？", "aggregate",
     "SELECT ROUND(AVG(amount),2) AS v FROM sales"),
    ("q7", "销售额最高的产品是哪一个？它的销售额是多少？", "top1",
     "SELECT ROUND(SUM(amount),2) AS v FROM sales GROUP BY product ORDER BY v DESC LIMIT 1"),
    ("q8", "成都的销售额是多少？", "filter",
     "SELECT ROUND(SUM(amount),2) AS v FROM sales WHERE city='成都'"),
    ("q9", "上海的销售额是多少？", "filter",
     "SELECT ROUND(SUM(amount),2) AS v FROM sales WHERE city='上海'"),
    ("q10", "2026 年 3 月的销售额是多少？", "filter",
     "SELECT ROUND(SUM(amount),2) AS v FROM sales "
     "WHERE date >= DATE '2026-03-01' AND date < DATE '2026-04-01'"),
    ("q11", "各城市的平均订单金额中，最高的是多少元？", "multistep",
     "SELECT ROUND(MAX(avg_amt),2) AS v FROM ("
     "SELECT AVG(amount) AS avg_amt FROM sales GROUP BY city)"),
    ("q12", "水果类的总销售额是多少？", "filter",
     "SELECT ROUND(SUM(amount),2) AS v FROM sales WHERE category='水果'"),
    ("q13", "卖出数量最多的产品，一共卖了多少件？", "top1",
     "SELECT SUM(qty) AS v FROM sales GROUP BY product ORDER BY v DESC LIMIT 1"),
    ("q14", "单价最高的产品，单价是多少？", "top1",
     "SELECT MAX(unit_price) AS v FROM sales"),
    ("q15", "金额超过 300 元的订单占总订单数的百分比是多少？", "ratio",
     "SELECT ROUND(100.0 * COUNT(*) FILTER (WHERE amount > 300) / COUNT(*), 2) AS v FROM sales"),
    ("q16", "肉蛋类商品在杭州的销售额是多少？", "multistep",
     "SELECT ROUND(SUM(amount),2) AS v FROM sales WHERE category='肉蛋' AND city='杭州'"),
    ("q17", "水果类销售额占总销售额的百分比是多少？", "ratio",
     "SELECT ROUND(100.0 * SUM(CASE WHEN category='水果' THEN amount END) "
     "/ SUM(amount), 2) AS v FROM sales"),
    ("q18", "3 月到 5 月这三个月的总销售额是多少？", "timeseries",
     "SELECT ROUND(SUM(amount),2) AS v FROM sales "
     "WHERE date >= DATE '2026-03-01' AND date < DATE '2026-06-01'"),
    ("q19", "平均每个订单卖了多少件商品？", "aggregate",
     "SELECT ROUND(AVG(qty),2) AS v FROM sales"),
    ("q20", "销售额最低的城市，销售额是多少？", "top1",
     "SELECT ROUND(SUM(amount),2) AS v FROM sales GROUP BY city ORDER BY v ASC LIMIT 1"),
    ("q21", "苹果这个产品一共卖出了多少件？", "filter",
     "SELECT SUM(qty) AS v FROM sales WHERE product='苹果'"),
    ("q22", "2 月份深圳的销售额是多少？", "multistep",
     "SELECT ROUND(SUM(amount),2) AS v FROM sales "
     "WHERE city='深圳' AND date >= DATE '2026-02-01' AND date < DATE '2026-03-01'"),
    ("q23", "销售额前 3 名的城市，销售额合计是多少？", "multistep",
     "SELECT ROUND(SUM(v),2) AS x FROM ("
     "SELECT SUM(amount) AS v FROM sales GROUP BY city ORDER BY v DESC LIMIT 3)"),
    ("q24", "销量（件数）最高的商品分类，一共卖了多少件？", "groupby",
     "SELECT SUM(qty) AS v FROM sales GROUP BY category ORDER BY v DESC LIMIT 1"),
]


def fmt(value) -> str:
    if isinstance(value, int):
        return str(value)
    if value is None:
        return ""
    return f"{float(value):.2f}"


def answer(con, sql: str) -> str:
    return fmt(con.execute(sql).fetchone()[0])


def _distinctive(expect: str) -> bool:
    """太短的期望值会被任意表格里的数字误命中，这类题直接判不合格。"""
    if len(expect) >= 4:
        return True
    try:
        return abs(float(expect)) >= 100
    except ValueError:
        return False


def main() -> None:
    con = duckdb.connect()
    con.execute(f"CREATE VIEW sales AS SELECT * FROM read_csv_auto('{DATA.as_posix()}')")

    items, bad = [], []
    for qid, question, tag, sql in QUESTS:
        expect = answer(con, sql)
        items.append({"id": qid, "question": question, "tag": tag,
                      "expect": expect, "gold_sql": " ".join(sql.split())})
        if not _distinctive(expect):
            bad.append((qid, expect))
        print(f"{qid:4s} {tag:10s} {expect:>10s}  {question}")

    if bad:
        print("\n期望值太短，容易被误匹配，请换题：", bad, file=sys.stderr)
        raise SystemExit(1)

    head = ("# 覆盖 top1 / count / aggregate / groupby / filter / timeseries / ratio / multistep\n"
            "# expect 由同题 gold_sql 在本数据集上实算得到（make key 可重算）\n"
            "# 数据源固定为 data/sample/sales.csv\n\n")
    OUT.write_text(head + yaml.safe_dump(items, allow_unicode=True, sort_keys=False),
                   encoding="utf-8")
    print(f"\n{len(items)} questions -> {OUT}")


if __name__ == "__main__":
    main()
