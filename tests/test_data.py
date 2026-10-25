from pathlib import Path

import pytest

import config
from mdagent.runtime import bootstrap_code, resolve, schema_text

SQLITE = config.ROOT / "data" / "sample" / "sales.sqlite"


def test_resolve_csv_directory():
    ds = resolve()
    assert ds.kind == "csv"
    assert "sales" in ds.tables
    assert "products" in ds.tables


def test_resolve_single_csv():
    ds = resolve(config.ROOT / "data" / "sample" / "sales.csv")
    assert ds.kind == "csv"
    assert ds.tables == ["sales"]


def test_resolve_sqlite():
    if not SQLITE.exists():
        pytest.skip("没有 sqlite 样例，先跑 data/generate_sample.py")
    ds = resolve(SQLITE)
    assert ds.kind == "sqlite"
    assert set(ds.tables) == {"sales", "products"}
    assert ds.db_file == "sales.sqlite"


def test_schema_text_lists_every_table():
    text = schema_text()
    assert "表 sales" in text
    assert "表 products" in text
    assert "supplier" in text


def test_bootstrap_creates_a_view_per_table():
    code = bootstrap_code()
    assert "CREATE VIEW sales" in code
    assert "CREATE VIEW products" in code
    assert "MDA_DATA" in code


def test_bootstrap_for_sqlite_attaches_database():
    if not SQLITE.exists():
        pytest.skip("没有 sqlite 样例，先跑 data/generate_sample.py")
    code = bootstrap_code(SQLITE)
    assert "LOAD sqlite" in code
    assert "MDA_DB" in code
    assert "CREATE VIEW sales" in code


def test_unknown_suffix_raises(tmp_path: Path):
    bogus = tmp_path / "note.txt"
    bogus.write_text("hi", encoding="utf-8")
    with pytest.raises(ValueError):
        resolve(bogus)
