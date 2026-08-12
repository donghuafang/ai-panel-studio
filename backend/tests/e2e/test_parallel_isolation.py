"""E2E 测试用例 2：多讨论并行隔离测试

两个独立 browser context 同时运行不同话题的讨论，验证状态互不污染。

运行：
    MOCK_LLM=true pytest tests/e2e/test_parallel_isolation.py -v --browser chromium
"""

import re
import json
import pytest
from playwright.sync_api import Browser, Page, expect


TOPIC_A = "量子计算的商业化前景"
TOPIC_B = "碳中和的技术路线选择"
EXPERT_COUNT_A = 3
EXPERT_COUNT_B = 5
BASE_URL = "http://localhost:5173"
API_BASE = "http://localhost:8000"


def _create_discussion_via_api(topic: str, expert_count: int) -> str:
    """通过 API 直接创建指定专家人数的讨论，返回 discussion_id。"""
    import urllib.request
    import urllib.error

    # Create discussion
    data = json.dumps({
        "topic": topic,
        "expert_count": expert_count,
        "max_rounds": 3,
    }).encode("utf-8")
    req = urllib.request.Request(
        f"{API_BASE}/api/discussions",
        data=data,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req) as resp:
        disc = json.loads(resp.read())
    return disc["id"]


def _create_and_start_discussion(page: Page, topic: str, expert_count: int):
    """辅助函数：通过 API 创建 + UI 生成嘉宾 + 确认进入演播厅。"""
    # 通过 API 创建讨论（支持自定义专家人数）
    disc_id = _create_discussion_via_api(topic, expert_count)

    # 导航到生成页面
    page.goto(f"{BASE_URL}/generate?discussion_id={disc_id}")
    page.wait_for_url(f"**/generate?discussion_id={disc_id}")

    # 填写话题（API 已设置，但 UI 可能需要显示）
    topic_input = page.locator('[data-testid="topic-input"]')
    try:
        topic_input.fill(topic)
    except Exception:
        pass  # 可能已预填充

    # 生成嘉宾
    page.click('[data-testid="generate-btn"]')
    page.locator('[data-testid="guest-card"]').first.wait_for(
        state="visible", timeout=15000
    )
    expected = expert_count + 1
    page.wait_for_function(
        f"document.querySelectorAll('[data-testid=\"guest-card\"]').length >= {expected}",
        timeout=15000,
    )

    # 确认进入演播厅
    page.click('[data-testid="confirm-btn"]')
    page.wait_for_url("**/studio/**", timeout=15000)

    # 等待讨论开始
    page.wait_for_function(
        """() => {
            const hasText = document.body.innerText.includes('讨论即将开始')
                || document.body.innerText.includes('讨论已结束');
            const speechCount = document.querySelectorAll('[data-testid="speech-item"]').length;
            return hasText || speechCount > 0;
        }""",
        timeout=20000,
    )

    return page.url


@pytest.mark.e2e
class TestParallelIsolation:
    """多讨论并行隔离测试。"""

    def test_parallel_discussion_isolation(self, browser: Browser):
        """两个独立 context 各自运行讨论，验证内容互不污染。"""

        # ── Step 1: 创建两个独立的 browser context ────────────
        ctx_a = browser.new_context()
        ctx_b = browser.new_context()
        page_a = ctx_a.new_page()
        page_b = ctx_b.new_page()

        try:
            # ── Step 2: Context A 发起话题 A ──
            url_a = _create_and_start_discussion(page_a, TOPIC_A, EXPERT_COUNT_A)

            # ── Step 3: Context B 发起话题 B ──
            url_b = _create_and_start_discussion(page_b, TOPIC_B, EXPERT_COUNT_B)

            # ── Step 4: 等待两个讨论各自产出一些发言 ──
            page_a.wait_for_function(
                "document.querySelectorAll('[data-testid=\"speech-item\"]').length >= 5",
                timeout=30000,
            )
            page_b.wait_for_function(
                "document.querySelectorAll('[data-testid=\"speech-item\"]').length >= 5",
                timeout=30000,
            )

            # ── Step 5: Context A transcript 隔离 ──
            transcript_a = page_a.locator('[data-testid="transcript-area"]').text_content() or ""

            # B 话题关键词不应出现在 A 的 transcript 中
            b_keywords = ["碳中和", "碳", "排放", "新能源"]
            for kw in b_keywords:
                assert kw not in transcript_a, (
                    f"Context A 的 Transcript 中包含了 B 话题关键词 '{kw}'，数据隔离失败"
                )

            # ── Step 6: Context B transcript 隔离 ──
            transcript_b = page_b.locator('[data-testid="transcript-area"]').text_content() or ""

            a_keywords = ["量子计算", "量子", "qubit", "量子位"]
            for kw in a_keywords:
                assert kw not in transcript_b, (
                    f"Context B 的 Transcript 中包含了 A 话题关键词 '{kw}'，数据隔离失败"
                )

            # ── Step 7: API 级别验证 ──
            # 从 URL 提取 discussion_id
            id_a = url_a.split("/")[-1]
            id_b = url_b.split("/")[-1]

            # 创建 API context 验证两个讨论的数据不同
            api_ctx = browser.new_context()
            api_page = api_ctx.new_page()

            # 请求 A 的共识
            api_page.goto(f"http://localhost:8000/api/discussions/{id_a}/consensus")
            body_a = api_page.locator("body").text_content() or "[]"

            # 请求 B 的共识
            api_page.goto(f"http://localhost:8000/api/discussions/{id_b}/consensus")
            body_b = api_page.locator("body").text_content() or "[]"

            # 验证两个讨论有不同的 ID（从 URL 已经确认不同）
            assert id_a != id_b, "两个讨论的 ID 应不同"

            # 验证数据不互相包含
            assert id_a not in body_b, "B 的响应中不应包含 A 的 discussion_id"
            assert id_b not in body_a, "A 的响应中不应包含 B 的 discussion_id"

            api_ctx.close()

        finally:
            ctx_a.close()
            ctx_b.close()
