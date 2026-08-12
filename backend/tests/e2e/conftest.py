"""E2E 测试基础设施 — 服务器生命周期管理 + Playwright fixtures。

用法:
    # 方式 1：手动启动服务器后运行
    # 终端 1: cd backend && MOCK_LLM=true uvicorn app.main:app --port 8000
    # 终端 2: cd frontend && npm run dev
    # 终端 3: cd backend && pytest tests/e2e/ -v

    # 方式 2：自动管理服务器（需要 --run-servers 标志）
    # cd backend && pytest tests/e2e/ -v --run-servers

注意：
- 后端运行在 http://localhost:8000，MOCK_LLM=true 必须设置
- 前端运行在 http://localhost:5173
- Playwright base_url 默认指向前端
"""

import os
import sys
import time
import signal
import socket
import subprocess
import pytest
from pathlib import Path


# ── 工具函数 ──────────────────────────────────────────────────

def _is_port_open(host: str, port: int) -> bool:
    """检查端口是否已被占用（服务是否在运行）。"""
    try:
        with socket.create_connection((host, port), timeout=1):
            return True
    except (socket.timeout, ConnectionRefusedError, OSError):
        return False


def _wait_for_port(host: str, port: int, timeout: int = 30) -> bool:
    """等待端口变为可用。"""
    start = time.time()
    while time.time() - start < timeout:
        if _is_port_open(host, port):
            return True
        time.sleep(0.5)
    return False


# ── 项目路径 ──────────────────────────────────────────────────

BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
FRONTEND_DIR = BACKEND_DIR.parent / "frontend"


# ── 服务器管理 Fixtures ──────────────────────────────────────

@pytest.fixture(scope="session")
def backend_server(request):
    """Session-scoped: 在后端未运行时自动启动它（需 --run-servers）。"""
    auto_start = request.config.getoption("--run-servers", default=False)

    if _is_port_open("localhost", 8000):
        yield "http://localhost:8000"
        return

    if not auto_start:
        pytest.skip(
            "后端未运行且未指定 --run-servers。"
            "请先手动启动: MOCK_LLM=true uvicorn app.main:app --port 8000"
        )

    env = os.environ.copy()
    env["MOCK_LLM"] = "true"

    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.main:app", "--port", "8000"],
        cwd=str(BACKEND_DIR),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    if not _wait_for_port("localhost", 8000, timeout=15):
        proc.kill()
        pytest.fail("后端启动超时（15s）")

    yield "http://localhost:8000"

    proc.send_signal(signal.SIGTERM)
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()


@pytest.fixture(scope="session")
def frontend_server(request):
    """Session-scoped: 在前端未运行时自动启动它（需 --run-servers）。"""
    auto_start = request.config.getoption("--run-servers", default=False)

    if _is_port_open("localhost", 5173):
        yield "http://localhost:5173"
        return

    if not auto_start:
        pytest.skip(
            "前端未运行且未指定 --run-servers。"
            "请先手动启动: cd frontend && npm run dev"
        )

    npm_cmd = "npm.cmd" if sys.platform == "win32" else "npm"
    proc = subprocess.Popen(
        [npm_cmd, "run", "dev"],
        cwd=str(FRONTEND_DIR),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    if not _wait_for_port("localhost", 5173, timeout=30):
        proc.kill()
        pytest.fail("前端启动超时（30s）")

    yield "http://localhost:5173"

    proc.send_signal(signal.SIGTERM)
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()


# ── E2E 数据库 Fixture ────────────────────────────────────────

@pytest.fixture(scope="function")
def e2e_db(backend_server, tmp_path):
    """创建临时 SQLite 数据库文件，通过环境变量覆盖默认路径。"""
    db_path = tmp_path / "test_e2e.db"
    old_db_url = os.environ.get("DATABASE_URL", "")

    os.environ["DATABASE_URL"] = f"sqlite:///{db_path}"

    yield db_path

    # 恢复
    if old_db_url:
        os.environ["DATABASE_URL"] = old_db_url
    else:
        os.environ.pop("DATABASE_URL", None)

    # 清理
    if db_path.exists():
        db_path.unlink()


# ── pytest 选项 ───────────────────────────────────────────────

def pytest_addoption(parser):
    parser.addoption(
        "--run-servers",
        action="store_true",
        default=False,
        help="自动启动后端和前端服务器（用于 CI/自动化）",
    )
