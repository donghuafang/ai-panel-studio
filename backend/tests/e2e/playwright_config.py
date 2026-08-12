"""Playwright E2E 测试配置 — AI Panel Studio.

运行方式:
    # 手动启动服务器后:
    pytest tests/e2e/ -v --browser chromium

    # 自动启动服务器（CI 模式）:
    pytest tests/e2e/ -v --browser chromium --run-servers

    # 并行运行（2 workers）:
    pytest tests/e2e/ -v --browser chromium -n 2

    # 多浏览器交叉验证:
    pytest tests/e2e/ -v --browser chromium --browser firefox
"""

import os
from pathlib import Path

# ── 基础配置 ──────────────────────────────────────────────────

# 前端 dev server 地址
BASE_URL = os.environ.get("E2E_BASE_URL", "http://localhost:5173")

# 截图/视频输出目录
SCREENSHOT_DIR = Path(__file__).parent / "tests" / "screenshots"
SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)


# ── pytest-playwright 配置（通过 pytest.ini 或 pyproject.toml） ─

# 这些配置在 pytest 命令行或 pytest.ini 中设置:
#
# [pytest]
# addopts =
#     --browser=chromium
#     --screenshot=only-on-failure
#     --video=retain-on-failure
#     --output=tests/e2e/results
#
# 或在运行时:
#   pytest tests/e2e/ --browser chromium --screenshot only-on-failure


def pytest_configure(config):
    """在 pytest 启动时配置 Playwright 相关设置。"""
    # 确保截图目录存在
    os.makedirs(str(SCREENSHOT_DIR), exist_ok=True)

    # 设置 Playwright base_url（如果未通过命令行指定）
    if not config.getoption("--base-url", default=None):
        config.option.base_url = BASE_URL
