"""生成 data/sample/sales.csv（固定随机种子，结果可复现）。

    python data/generate_sample.py
"""

import csv
import random
from datetime import date, timedelta
from pathlib import Path

SEED = 20261022
ROWS = 240
START = date(2026, 1, 1)
DAYS = 181

CITIES = ["杭州", "上海", "北京", "成都", "广州", "深圳"]

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

OUT = Path(__file__).parent / "sample" / "sales.csv"


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


if __name__ == "__main__":
    main()
