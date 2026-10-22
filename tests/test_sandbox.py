from pathlib import Path

import pytest

import config
from mdagent.runtime import active_backend, docker_ready, read_schema, run_code


def test_read_schema_contains_columns():
    schema = read_schema(config.DATA_PATH)
    assert "city" in schema
    assert "amount" in schema
    assert "样例行" in schema


def test_run_code_ok():
    ok, out, err = run_code("print(6 * 7)")
    assert ok
    assert out.strip() == "42"


def test_run_code_can_read_data_via_env():
    code = (
        "import os, duckdb\n"
        "con = duckdb.connect()\n"
        "print(con.execute(\"SELECT COUNT(*) FROM read_csv_auto('\" + os.environ['MDA_DATA'] + \"')\").fetchone()[0])\n"
    )
    ok, out, err = run_code(code)
    assert ok, err
    assert out.strip().isdigit() and int(out.strip()) > 0


def test_run_code_reports_error():
    ok, out, err = run_code("raise ValueError('boom')")
    assert not ok
    assert "boom" in err


def test_run_code_timeout():
    ok, out, err = run_code("import time\ntime.sleep(30)", timeout=2)
    assert not ok
    assert "超时" in err


def test_subprocess_backend_explicitly():
    ok, out, _ = run_code("print(1 + 1)", backend="subprocess")
    assert ok
    assert out.strip() == "2"


@pytest.mark.skipif(not docker_ready(), reason="需要 Docker Desktop + mdagent-sandbox 镜像")
def test_docker_backend_has_no_network_and_readonly_fs():
    code = (
        "import os, socket, duckdb\n"
        "con = duckdb.connect()\n"
        "n = con.execute(\"SELECT COUNT(*) FROM read_csv_auto('\" + os.environ['MDA_DATA'] + \"')\").fetchone()[0]\n"
        "print('rows', n)\n"
        "try:\n"
        "    open('/work/x', 'w').write('x')\n"
        "    print('writable')\n"
        "except OSError:\n"
        "    print('readonly')\n"
        "try:\n"
        "    socket.create_connection(('1.1.1.1', 53), timeout=2)\n"
        "    print('network-ok')\n"
        "except OSError:\n"
        "    print('network-blocked')\n"
    )
    ok, out, err = run_code(code, backend="docker")
    assert ok, err
    assert "readonly" in out
    assert "network-blocked" in out


def test_docker_backend_reports_unavailable_clearly():
    if docker_ready():
        pytest.skip("本机 Docker 可用，走正常路径")
    ok, out, err = run_code("print(1)", backend="docker")
    assert not ok
    assert "Docker" in err


def test_active_backend_is_known_value():
    assert active_backend() in ("subprocess", "docker", "docker(不可用→subprocess)")
