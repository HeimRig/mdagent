"""数据源抽象。

三种形态统一成「一份表清单 + 一段沙箱引导代码」：

- 单个 `.csv`            → 一张表，表名取文件名
- 一个目录               → 目录下每个 `.csv` 一张表
- `.duckdb` / `.db`      → duckdb 数据库文件
- `.sqlite` / `.sqlite3` → SQLite 文件，靠 duckdb 的 sqlite 扩展读
"""

import sqlite3
from dataclasses import dataclass
from pathlib import Path

import duckdb

import config

CSV_SUFFIX = ".csv"
DB_SUFFIXES = {".duckdb", ".db"}
SQLITE_SUFFIXES = {".sqlite", ".sqlite3"}
SAMPLE_ROWS = 3


@dataclass(frozen=True)
class DataSource:
    root: Path
    kind: str
    tables: list[str]
    db_file: str = ""

    @property
    def is_sqlite(self) -> bool:
        return self.kind == "sqlite"

    @property
    def needs_extension(self) -> bool:
        return self.kind == "sqlite"


def resolve(source=None) -> DataSource:
    path = Path(source or config.DATA_SOURCE).resolve()

    if path.is_dir():
        files = sorted(p for p in path.glob(f"*{CSV_SUFFIX}") if p.is_file())
        if not files:
            raise ValueError(f"目录里没有 CSV：{path}")
        return DataSource(root=path, kind="csv", tables=[p.stem for p in files])

    if not path.exists():
        raise FileNotFoundError(f"数据源不存在：{path}")

    suffix = path.suffix.lower()
    if suffix == CSV_SUFFIX:
        return DataSource(root=path.parent, kind="csv", tables=[path.stem])
    if suffix in DB_SUFFIXES:
        return DataSource(root=path.parent, kind="db",
                          tables=_duckdb_tables(path), db_file=path.name)
    if suffix in SQLITE_SUFFIXES:
        return DataSource(root=path.parent, kind="sqlite",
                          tables=_sqlite_tables(path), db_file=path.name)
    raise ValueError(f"不认识的数据源类型：{path.suffix}")


def _duckdb_tables(path: Path) -> list[str]:
    con = duckdb.connect(str(path), read_only=True)
    try:
        rows = con.execute(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema = 'main' ORDER BY table_name"
        ).fetchall()
    finally:
        con.close()
    return [r[0] for r in rows]


def _sqlite_tables(path: Path) -> list[str]:
    con = sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True)
    try:
        rows = con.execute(
            "SELECT name FROM sqlite_master WHERE type='table' "
            "AND name NOT LIKE 'sqlite_%' ORDER BY name"
        ).fetchall()
    finally:
        con.close()
    return [r[0] for r in rows]


def _csv_path(ds: DataSource, name: str) -> Path:
    return ds.root / f"{name}{CSV_SUFFIX}"


def _block(con, name: str, rel: str, sample_rows: int) -> str:
    cols = con.execute(f"DESCRIBE SELECT * FROM {rel}").fetchall()
    total = con.execute(f"SELECT COUNT(*) FROM {rel}").fetchone()[0]
    head = con.execute(f"SELECT * FROM {rel} LIMIT {sample_rows}").fetchdf()
    lines = [f"表 {name}（{total} 行）", "字段:"]
    lines.extend(f"  - {c[0]}: {c[1]}" for c in cols)
    lines.append("样例行:")
    lines.append(head.to_string(index=False))
    return "\n".join(lines)


def _sqlite_block(path: Path, name: str, sample_rows: int) -> str:
    con = sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True)
    try:
        cols = con.execute(f'PRAGMA table_info("{name}")').fetchall()
        total = con.execute(f'SELECT COUNT(*) FROM "{name}"').fetchone()[0]
        cur = con.execute(f'SELECT * FROM "{name}" LIMIT {sample_rows}')
        head = cur.fetchall()
    finally:
        con.close()

    lines = [f"表 {name}（{total} 行）", "字段:"]
    lines.extend(f"  - {c[1]}: {c[2]}" for c in cols)
    lines.append("样例行:")
    lines.extend(" | ".join("" if v is None else str(v) for v in row) for row in head)
    return "\n".join(lines)


def schema_text(source=None, sample_rows: int = SAMPLE_ROWS) -> str:
    ds = resolve(source)

    if ds.kind == "csv":
        con = duckdb.connect()
        try:
            blocks = [
                _block(con, name, f"read_csv_auto('{_csv_path(ds, name).as_posix()}')", sample_rows)
                for name in ds.tables
            ]
        finally:
            con.close()
        return "\n\n".join(blocks)

    if ds.kind == "db":
        con = duckdb.connect(str(ds.root / ds.db_file), read_only=True)
        try:
            blocks = [_block(con, name, f'"{name}"', sample_rows) for name in ds.tables]
        finally:
            con.close()
        return "\n\n".join(blocks)

    return "\n\n".join(_sqlite_block(ds.root / ds.db_file, name, sample_rows) for name in ds.tables)


def bootstrap_code(source=None) -> str:
    """沙箱里要原样保留的前几行：打开数据源并把每张表建成视图。"""
    ds = resolve(source)

    if ds.kind == "csv":
        lines = [
            "import os",
            "import duckdb",
            "",
            'DATA = os.environ["MDA_DATA"]',
            "con = duckdb.connect()",
        ]
        for name in ds.tables:
            lines.append(
                f"""con.execute("CREATE VIEW {name} AS SELECT * FROM read_csv_auto('" + DATA + "/{name}.csv')")"""
            )
        return "\n".join(lines)

    if ds.kind == "db":
        return "\n".join([
            "import os",
            "import duckdb",
            "",
            'con = duckdb.connect(os.environ["MDA_DB"], read_only=True)',
        ])

    lines = [
        "import os",
        "import duckdb",
        "",
        "con = duckdb.connect()",
        'con.execute("INSTALL sqlite")',
        'con.execute("LOAD sqlite")',
        """con.execute("ATTACH '" + os.environ["MDA_DB"] + "' AS src (TYPE sqlite, READ_ONLY)")""",
    ]
    for name in ds.tables:
        lines.append(f'con.execute("CREATE VIEW {name} AS SELECT * FROM src.{name}")')
    return "\n".join(lines)
