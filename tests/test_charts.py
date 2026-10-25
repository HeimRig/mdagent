from pathlib import Path

import pandas as pd

from mdagent.charts import build_chart, parse_table

TABLE = """category  total_sales
      肉蛋      28920.0
      乳品       8607.0
      水果       8450.3
      蔬菜       3143.5"""


def test_parse_table_reads_columns_and_dtypes():
    df = parse_table(TABLE)
    assert list(df.columns) == ["category", "total_sales"]
    assert len(df) == 4
    assert pd.api.types.is_numeric_dtype(df["total_sales"])
    assert df["total_sales"].max() == 28920.0


def test_parse_table_returns_none_without_table():
    assert parse_table("rows 240") is None
    assert parse_table("") is None


def test_build_chart_writes_png(tmp_path: Path):
    path = build_chart(TABLE, "各类目的总销售额排名", out_dir=tmp_path)
    assert path is not None
    assert path.suffix == ".png"
    assert path.stat().st_size > 1000


def test_build_chart_skips_single_row(tmp_path: Path):
    single = "city  total_sales\n  杭州      11986.5"
    assert build_chart(single, "哪个城市最高", out_dir=tmp_path) is None


def test_build_chart_skips_text_only_result(tmp_path: Path):
    assert build_chart("## 结论\n\n杭州最高。", "问题", out_dir=tmp_path) is None
