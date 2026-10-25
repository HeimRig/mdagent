"""受限执行沙箱。

两种后端，接口一致（`run_code` 签名不变）：

- `subprocess`：子进程 + 超时 + 抹掉密钥环境变量。本机开发够用，但**不是安全边界**，
  生成的代码仍能读文件系统、能联网。
- `docker`：`--network=none --read-only` + 只读挂载数据 + 内存/CPU 限额，真隔离。
  镜像用 `make docker-image` 构建，镜像不在就自动回退子进程（`auto` 模式）。

数据源可以是单个 CSV、目录或数据库文件，统一由 `data.py` 解析。
"""

import os
import shutil
import subprocess
import sys
import tempfile
import uuid
from pathlib import Path

import config
from .data import DataSource, resolve, schema_text

_DOCKER_OK: bool | None = None
MOUNT = "/data"


def read_schema(source=None, sample_rows: int = 3) -> str:
    """读出所有表的结构与样例行，喂给 Planner / Coder，避免它们瞎猜字段名。"""
    return schema_text(source, sample_rows)


_SECRET_HINTS = ("API_KEY", "TOKEN", "SECRET", "PASSWORD")


def _safe_env() -> dict[str, str]:
    """继承运行环境，但抹掉所有像密钥的变量，避免生成的代码把它们读走。"""
    return {k: v for k, v in os.environ.items()
            if not any(h in k.upper() for h in _SECRET_HINTS)}


def _env_for(ds: DataSource, mount: str) -> dict[str, str]:
    env = _safe_env()
    env["MDA_DATA"] = mount
    env["PYTHONIOENCODING"] = "utf-8"
    if ds.db_file:
        env["MDA_DB"] = f"{mount}/{ds.db_file}"
    return env


def docker_ready() -> bool:
    """docker 命令在，且沙箱镜像已经构建过。"""
    global _DOCKER_OK
    if _DOCKER_OK is None:
        exe = shutil.which("docker")
        if not exe:
            _DOCKER_OK = False
        else:
            try:
                proc = subprocess.run([exe, "image", "inspect", config.SANDBOX_IMAGE],
                                      capture_output=True, timeout=20)
                _DOCKER_OK = proc.returncode == 0
            except (OSError, subprocess.SubprocessError):
                _DOCKER_OK = False
    return _DOCKER_OK


def active_backend() -> str:
    """实际生效的后端，写进报告用。"""
    backend = str(config.SANDBOX_BACKEND).lower()
    if backend == "auto":
        return "docker" if docker_ready() else "subprocess"
    if backend == "docker":
        return "docker" if docker_ready() else "docker(不可用→subprocess)"
    return "subprocess"


def _run_subprocess(code: str, ds: DataSource, timeout: int) -> tuple[bool, str, str]:
    with tempfile.TemporaryDirectory(prefix="mdagent_") as tmp:
        script = Path(tmp) / "snippet.py"
        script.write_text(code, encoding="utf-8")
        try:
            proc = subprocess.run(
                [sys.executable, str(script)],
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=tmp,
                env=_env_for(ds, ds.root.as_posix()),
                encoding="utf-8",
                errors="replace",
            )
        except subprocess.TimeoutExpired:
            return False, "", f"执行超时（>{timeout}s）"

    return proc.returncode == 0, (proc.stdout or "").strip(), (proc.stderr or "").strip()


def _run_docker(code: str, ds: DataSource, timeout: int) -> tuple[bool, str, str]:
    name = f"mdagent-{uuid.uuid4().hex[:10]}"
    workdir = Path(tempfile.mkdtemp(prefix="mdagent_"))
    try:
        (workdir / "snippet.py").write_text(code, encoding="utf-8")
        cmd = [
            "docker", "run", "--rm", "--name", name,
            "--network=none", "--read-only", "--tmpfs", "/tmp",
            "--memory", "512m", "--cpus", "1", "--pids-limit", "128",
            "-e", "PYTHONDONTWRITEBYTECODE=1",
            "-v", f"{workdir.as_posix()}:/work:ro",
            "-v", f"{ds.root.as_posix()}:{MOUNT}:ro",
            "-w", "/work",
        ]
        for key, val in _env_for(ds, MOUNT).items():
            if key.startswith("MDA_"):
                cmd += ["-e", f"{key}={val}"]
        cmd += [config.SANDBOX_IMAGE, "python", "/work/snippet.py"]

        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout,
                                  encoding="utf-8", errors="replace")
        except subprocess.TimeoutExpired:
            subprocess.run(["docker", "kill", name], capture_output=True, timeout=20)
            return False, "", f"执行超时（>{timeout}s）"
        return proc.returncode == 0, (proc.stdout or "").strip(), (proc.stderr or "").strip()
    finally:
        shutil.rmtree(workdir, ignore_errors=True)


def run_code(code: str, source=None, timeout: int | None = None,
             backend: str | None = None) -> tuple[bool, str, str]:
    """执行生成的代码，返回 (是否成功, stdout, stderr)。"""
    ds = resolve(source)
    timeout = timeout or config.SANDBOX_TIMEOUT
    backend = str(backend or config.SANDBOX_BACKEND).lower()

    if backend in ("auto", "docker") and docker_ready():
        return _run_docker(code, ds, timeout)
    if backend == "docker":
        return False, "", (
            "Docker 后端不可用：确认 Docker Desktop 已启动，"
            f"且已构建镜像（docker build -t {config.SANDBOX_IMAGE} docker/）"
        )
    return _run_subprocess(code, ds, timeout)
