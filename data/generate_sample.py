"""生成 data/sample/ 下的样例数据（固定随机种子，结果可复现）。

    python data/generate_sample.py

产出三种形态，内容一致，方便验证不同的数据源：
    sales.csv + products.csv   CSV 目录（默认用这个）
    sales.sqlite               同一个库里的两张表
"""

import csv
import random
import sqlite3
from datetime import date, timedelta
from pathlib import Path

import pandas as pd

SEED = 20261022
ROWS = 240
START = date(2026, 1, 1)
DAYS = 181

CITIES = ["杭州", "上海", "北京", "成都", "广州", "深圳"]

SUPPLIERS = ["杭州生鲜", "上海果蔬", "山东农产", "云南直供"]

PRODUCTS = [
    ("苹果", "水果", 5.50),
    ("香蕉", "水果", 4.20),
    ("橙子", "水果", 6.80),
    ("西瓜", "水果", 2.80),
    ("白菜", "蔬菜", 2.00),
    ("菠菜", "蔬菜", 3.00),
    ("黄瓜", "蔬菜", 2.50),
    ("番茄", "蔬菜", 4.00),
    ("鸡蛋", "肉蛋", 1.20),
    ("牛肉", "肉蛋", 45.00),
    ("猪肉", "肉蛋", 28.00),
    ("牛奶", "乳品", 12.50),
    ("酸奶", "乳品", 9.00),
]

HERE = Path(__file__).parent / "sample"
OUT = HERE / "sales.csv"
OUT_PRODUCTS = HERE / "products.csv"
OUT_SQLITE = HERE / "sales.sqlite"


def main() -> None:
    rng = random.Random(SEED)
    rows = []
    for i in range(1, ROWS + 1):
        product, category, price = rng.choice(PRODUCTS)
        day = START + timedelta(days=rng.randrange(DAYS))
        qty = rng.randint(4, 40)
        rows.append([
            f"O{i:04d}",
            day.isoformat(),
            rng.choice(CITIES),
            product,
            category,
            qty,
            f"{price:.2f}",
            f"{qty * price:.2f}",
        ])

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["order_id", "date", "city", "product", "category", "qty", "unit_price", "amount"])
        w.writerows(rows)
    print(f"wrote {len(rows)} rows -> {OUT}")

    products = []
    for product, category, price in PRODUCTS:
        cost = price * rng.uniform(0.55, 0.75)
        products.append([
            product,
            category,
            rng.choice(SUPPLIERS),
            f"{cost:.2f}",
            rng.choice([3, 7, 15, 30, 90]),
        ])

    with OUT_PRODUCTS.open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["product", "category", "supplier", "cost_per_unit", "shelf_life_days"])
        w.writerows(products)
    print(f"wrote {len(products)} rows -> {OUT_PRODUCTS}")

    if OUT_SQLITE.exists():
        OUT_SQLITE.unlink()
    conn = sqlite3.connect(OUT_SQLITE)
    try:
        pd.read_csv(OUT).to_sql("sales", conn, index=False, if_exists="replace")
        pd.read_csv(OUT_PRODUCTS).to_sql("products", conn, index=False, if_exists="replace")
    finally:
        conn.close()
    print(f"wrote 2 tables -> {OUT_SQLITE}")


if __name__ == "__main__":
    main()
