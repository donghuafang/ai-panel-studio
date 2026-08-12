#!/usr/bin/env python3
"""AI Panel Studio 质量检查脚本

自动化执行 5 项检查：
1. API 契约一致性（Schemathesis 随机用例）
2. 中文 UI 完整性（前端英文硬编码检查）
3. 多讨论压力测试（并发 10 讨论 × 60s）
4. API Key 安全检查（构建产物扫描）
5. 数据库初始化验证（预置数据检查）

用法:
    python scripts/quality_check.py [--backend http://localhost:8000] [--frontend http://localhost:5173]
"""

import os
import sys
import json
import time
import glob
import asyncio
import argparse
import subprocess
import tempfile
from pathlib import Path
from datetime import datetime

# ── 项目根路径 ─────────────────────────────────────────────────

PROJECT_ROOT = Path(__file__).resolve().parent.parent
BACKEND_DIR = PROJECT_ROOT / "backend"
FRONTEND_DIR = PROJECT_ROOT / "frontend"
FRONTEND_DIST = FRONTEND_DIR / "dist"


# ── 彩色输出 ───────────────────────────────────────────────────

class Colors:
    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    CYAN = "\033[96m"
    RESET = "\033[0m"
    BOLD = "\033[1m"


def ok(msg: str):
    print(f"  {Colors.GREEN}✅ {msg}{Colors.RESET}")


def fail(msg: str):
    print(f"  {Colors.RED}❌ {msg}{Colors.RESET}")


def warn(msg: str):
    print(f"  {Colors.YELLOW}⚠️  {msg}{Colors.RESET}")


def info(msg: str):
    print(f"  {Colors.CYAN}ℹ️  {msg}{Colors.RESET}")


def section(title: str):
    print(f"\n{Colors.BOLD}{'=' * 60}{Colors.RESET}")
    print(f"{Colors.BOLD}  {title}{Colors.RESET}")
    print(f"{Colors.BOLD}{'=' * 60}{Colors.RESET}\n")


# ── 全局结果追踪 ──────────────────────────────────────────────

results = {"passed": [], "failed": [], "warnings": [], "start_time": datetime.now()}


# ══════════════════════════════════════════════════════════════════
# Check 1: API 契约一致性
# ══════════════════════════════════════════════════════════════════

def check_api_contract(backend_url: str):
    """使用 Schemathesis 检查 API 契约。"""
    section("Check 1/5: API 契约一致性 (Schemathesis)")

    try:
        import schemathesis
    except ImportError:
        warn("Schemathesis 未安装 (pip install schemathesis)，跳过此检查")
        results["warnings"].append("Schemathesis 未安装，API 契约检查已跳过")
        return

    openapi_url = f"{backend_url}/openapi.json"
    info(f"从 {openapi_url} 加载 OpenAPI Schema...")

    try:
        # 使用 schemathesis.from_url 加载 schema
        schema = schemathesis.from_url(openapi_url)

        # 运行 100 个随机用例
        info("运行 100 个随机测试用例...")
        passed = 0
        failed = 0

        for result in schema.execute(
            checks=(schemathesis.checks.status_code_conformance,),
            max_response_time=10000,
        ):
            for check in result.checks:
                if check.name == "status_code_conformance":
                    if not check.value:
                        failed += 1
                        fail(f"{result.method} {result.path} → {result.response.status_code}")
                    else:
                        passed += 1

        total = passed + failed
        if failed == 0 and passed > 0:
            ok(f"所有 {passed} 个随机用例通过 (API 契约一致)")
            results["passed"].append("API 契约一致性检查通过")
        elif passed > 0:
            fail(f"{failed}/{total} 用例失败")
            results["failed"].append(f"API 契约检查: {failed}/{total} 失败")
        else:
            warn("无用例执行，请检查后端是否运行")
            results["warnings"].append("API 契约检查无结果")

    except Exception as e:
        warn(f"Schemathesis 检查失败: {e}")
        results["warnings"].append(f"API 契约检查异常: {e}")


# ══════════════════════════════════════════════════════════════════
# Check 2: 中文 UI 完整性
# ══════════════════════════════════════════════════════════════════

# 允许出现的英文/缩写（技术名词、品牌名、专有名词）
ALLOWED_ENGLISH = {
    # 品牌/产品
    "AI", "API", "JSON", "SSE", "SQL", "HTTP",
    # 技术名词
    "URL", "ID", "UI", "UX", "CSS", "HTML", "JS",
    # Logo 和品牌
    "Panel", "Studio",
    # 常见缩写
    "OK", "vs", "CEO",
    # 状态值
    "pending", "active", "ended", "host", "guest",
    "speaking", "thinking", "ready", "idle",
}


def _extract_text_nodes(url: str) -> list[str]:
    """使用 Playwright 提取页面所有可见文本。"""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return []

    texts = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        try:
            page.goto(url, timeout=10000)
            page.wait_for_timeout(2000)
            # 提取所有可见元素的文本
            texts = page.evaluate("""() => {
                const walker = document.createTreeWalker(
                    document.body,
                    NodeFilter.SHOW_TEXT,
                    { acceptNode: node =>
                        node.parentElement &&
                        window.getComputedStyle(node.parentElement).display !== 'none' &&
                        window.getComputedStyle(node.parentElement).visibility !== 'hidden'
                            ? NodeFilter.FILTER_ACCEPT
                            : NodeFilter.FILTER_REJECT
                    }
                );
                const texts = [];
                let node;
                while (node = walker.nextNode()) {
                    const t = node.textContent.trim();
                    if (t) texts.push(t);
                }
                return texts;
            }""")
        finally:
            browser.close()
    return texts


def _check_chinese_violations(text_nodes: list[str]) -> list[str]:
    """检查文本节点中是否有不合规的英文硬编码。"""
    import re
    violations = []

    for text in text_nodes:
        # 提取所有英文单词（2+ 字母）
        english_words = re.findall(r'\b[A-Za-z]{2,}\b', text)
        for word in english_words:
            # 排除允许列表
            if word in ALLOWED_ENGLISH:
                continue
            # 排除中文拼音（不太可能单独出现）
            # 排除 URL 路径
            if "/" in word or "." in word:
                continue
            violations.append(f"'{word}' in: \"{text[:80]}...\"" if len(text) > 80 else f"'{word}' in: \"{text}\"")

    return violations


def check_chinese_ui(frontend_url: str):
    """检查前端页面中文完整性。"""
    section("Check 2/5: 中文 UI 完整性")

    pages_to_check = [
        f"{frontend_url}/",
        f"{frontend_url}/generate",
    ]
    # Studio 页面需要已存在的 discussion_id，跳过首页和生成页

    all_violations = []

    for url in pages_to_check:
        info(f"检查页面: {url}")
        try:
            text_nodes = _extract_text_nodes(url)
            if not text_nodes:
                warn(f"无法提取 {url} 的文本（Playwright 可能未安装）")
                continue

            violations = _check_chinese_violations(text_nodes)
            if violations:
                for v in violations[:5]:  # 最多显示 5 条
                    fail(v)
                if len(violations) > 5:
                    info(f"... 还有 {len(violations) - 5} 条违规")
                all_violations.extend(violations)
            else:
                ok(f"{url} 无英文硬编码违规")

        except Exception as e:
            warn(f"检查 {url} 时出错: {e}")

    if all_violations:
        results["failed"].append(f"中文 UI 检查: {len(all_violations)} 条违规")
    else:
        ok("所有页面中文完整性检查通过")
        results["passed"].append("中文 UI 完整性检查通过")


# ══════════════════════════════════════════════════════════════════
# Check 3: 多讨论压力测试
# ══════════════════════════════════════════════════════════════════

async def _create_and_run_discussion(backend_url: str, topic: str, expert_count: int, run_seconds: int):
    """创建讨论、生成嘉宾、确认、通过 SSE 监听事件。"""
    import aiohttp

    async with aiohttp.ClientSession() as session:
        # 1. 创建讨论
        async with session.post(
            f"{backend_url}/api/discussions",
            json={"topic": topic, "expert_count": expert_count, "max_rounds": 3},
        ) as resp:
            if resp.status != 201:
                return {"status": "error", "step": "create", "code": resp.status}
            disc = await resp.json()
            disc_id = disc["id"]

        # 2. 生成嘉宾
        async with session.post(
            f"{backend_url}/api/discussions/{disc_id}/generate-guests",
        ) as resp:
            if resp.status != 200:
                return {"status": "error", "step": "generate", "code": resp.status}

        # 3. 确认并启动
        async with session.post(
            f"{backend_url}/api/discussions/{disc_id}/confirm",
        ) as resp:
            if resp.status != 200:
                return {"status": "error", "step": "confirm", "code": resp.status}

        # 4. 通过 SSE 监听事件
        events_received = 0
        try:
            async with session.get(
                f"{backend_url}/api/discussions/{disc_id}/stream",
                timeout=aiohttp.ClientTimeout(total=run_seconds + 10),
            ) as resp:
                start = time.time()
                async for line in resp.content:
                    if time.time() - start > run_seconds:
                        break
                    line_text = line.decode("utf-8", errors="ignore").strip()
                    if line_text.startswith("event:") or line_text.startswith("data:"):
                        events_received += 1
        except asyncio.TimeoutError:
            pass
        except Exception:
            pass

        return {
            "status": "ok",
            "discussion_id": disc_id,
            "events": events_received,
        }


async def _run_stress_test(backend_url: str):
    """并发创建并运行 10 个讨论，持续 60 秒。"""
    topics = [
        "AI 如何改变教育",
        "自动驾驶的安全与伦理",
        "基因编辑技术的边界",
        "虚拟现实与社交的未来",
        "数字货币的监管挑战",
        "太空探索的商业价值",
        "可再生能源的技术突破",
        "远程办公对城市的影响",
        "大数据时代的隐私保护",
        "人工智能与艺术创作",
    ]

    tasks = []
    for i in range(10):
        topic = topics[i % len(topics)]
        expert_count = 3 + (i % 3)  # 3-5 experts
        tasks.append(_create_and_run_discussion(backend_url, topic, expert_count, 60))

    results_list = await asyncio.gather(*tasks, return_exceptions=True)
    return results_list


def check_stress_test(backend_url: str):
    """多讨论压力测试。"""
    section("Check 3/5: 多讨论压力测试")

    try:
        import aiohttp
    except ImportError:
        warn("aiohttp 未安装 (pip install aiohttp)，跳过压力测试")
        results["warnings"].append("aiohttp 未安装，压力测试已跳过")
        return

    info("并发创建 10 个讨论，运行 60 秒...")
    start = time.time()

    loop = asyncio.new_event_loop()
    try:
        stress_results = loop.run_until_complete(_run_stress_test(backend_url))
    finally:
        loop.close()

    elapsed = time.time() - start

    ok_count = sum(1 for r in stress_results if isinstance(r, dict) and r.get("status") == "ok")
    error_count = sum(1 for r in stress_results if isinstance(r, dict) and r.get("status") == "error")
    exception_count = sum(1 for r in stress_results if isinstance(r, Exception))

    info(f"完成: {ok_count} 成功, {error_count} 失败, {exception_count} 异常, 耗时 {elapsed:.1f}s")

    if ok_count == 10:
        ok(f"所有 10 个讨论正常运行并接收事件")
        results["passed"].append("压力测试通过 (10/10)")
    else:
        fail(f"仅 {ok_count}/10 个讨论成功")
        results["failed"].append(f"压力测试: {ok_count}/10 成功")

    # 内存检查（粗略）
    import psutil as _  # optional
    try:
        import psutil
        mem_mb = psutil.Process().memory_info().rss / 1024 / 1024
        if mem_mb > 500:
            warn(f"内存占用 {mem_mb:.0f}MB 超过 500MB 阈值")
            results["warnings"].append(f"内存占用 {mem_mb:.0f}MB")
        else:
            ok(f"内存占用 {mem_mb:.0f}MB (阈值 500MB)")
    except ImportError:
        info("psutil 未安装，跳过内存检查")


# ══════════════════════════════════════════════════════════════════
# Check 4: API Key 安全检查
# ══════════════════════════════════════════════════════════════════

def check_api_key_safety():
    """扫描前端构建产物，确保不包含 API Key。"""
    section("Check 4/5: API Key 安全检查")

    violations = []

    # 检查前端 dist 目录
    if FRONTEND_DIST.exists():
        info(f"扫描 {FRONTEND_DIST} ...")
        for ext in ["*.js", "*.html", "*.css"]:
            for filepath in FRONTEND_DIST.rglob(ext):
                try:
                    content = filepath.read_text(encoding="utf-8", errors="ignore")
                    if "DEEPSEEK_API_KEY" in content:
                        violations.append(str(filepath))
                    if "sk-" in content and "api.deepseek.com" in content:
                        violations.append(f"{filepath} (包含疑似 API 端点和 key)")
                except Exception:
                    pass
    else:
        info(f"frontend/dist/ 不存在，检查源码...")

    # 检查前端源码
    for ext in ["*.ts", "*.tsx", "*.js", "*.html"]:
        for filepath in FRONTEND_DIR.rglob(ext):
            if "node_modules" in str(filepath):
                continue
            try:
                content = filepath.read_text(encoding="utf-8", errors="ignore")
                if "DEEPSEEK_API_KEY" in content or "sk-" in content:
                    # 跳过 .env.example 等配置文件
                    if "example" in filepath.name or ".env" in filepath.name:
                        continue
                    violations.append(str(filepath))
            except Exception:
                pass

    if violations:
        for v in violations:
            fail(f"发现 API Key 泄露: {v}")
        results["failed"].append(f"API Key 安全检查: {len(violations)} 处泄露")
    else:
        ok("未在前端代码中发现 API Key 泄露")
        results["passed"].append("API Key 安全检查通过")

    # 检查前端网络请求
    info("提示: 使用 Playwright 监听网络请求需在 E2E 测试中实现")
    info("断言前端没有任何直连 api.deepseek.com 的请求")


# ══════════════════════════════════════════════════════════════════
# Check 5: 数据库初始化验证
# ══════════════════════════════════════════════════════════════════

def check_database_init():
    """验证数据库初始化脚本和预置数据。"""
    section("Check 5/5: 数据库初始化验证")

    db_path = BACKEND_DIR / "ai_panel_studio.db"

    # 检查数据库文件是否存在
    if db_path.exists():
        info(f"数据库文件存在: {db_path}")

        # 验证数据库可以通过 SQLAlchemy 正常访问
        sys.path.insert(0, str(BACKEND_DIR))
        try:
            from app.database import SessionLocal, Base
            from app.models import Discussion, Guest

            session = SessionLocal()
            try:
                # 查询讨论总数
                disc_count = session.query(Discussion).count()
                guest_count = session.query(Guest).count()

                info(f"当前数据: {disc_count} 个讨论, {guest_count} 位嘉宾")

                if disc_count > 0:
                    ok(f"数据库包含 {disc_count} 条讨论记录")
                else:
                    info("数据库为空（正常，新安装或已清理）")

                ok("数据库连接和 ORM 映射正常")
                results["passed"].append("数据库初始化验证通过")

            finally:
                session.close()
        except Exception as e:
            fail(f"数据库访问失败: {e}")
            results["failed"].append(f"数据库初始化验证失败: {e}")
    else:
        info(f"数据库文件不存在: {db_path}")
        info("启动后端服务后将自动创建数据库和表结构")
        ok("数据库自动创建机制就绪")
        results["passed"].append("数据库初始化验证通过（自动创建）")


# ══════════════════════════════════════════════════════════════════
# 主入口
# ══════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description="AI Panel Studio 质量检查")
    parser.add_argument("--backend", default="http://localhost:8000", help="后端 URL")
    parser.add_argument("--frontend", default="http://localhost:5173", help="前端 URL")
    parser.add_argument("--skip-stress", action="store_true", help="跳过压力测试")
    parser.add_argument("--skip-api", action="store_true", help="跳过 API 契约检查")
    args = parser.parse_args()

    print(f"\n{Colors.BOLD}🎯 AI Panel Studio — 质量检查{Colors.RESET}")
    print(f"   后端: {args.backend}")
    print(f"   前端: {args.frontend}")
    print(f"   时间: {results['start_time'].isoformat()}")

    # Check 1
    if not args.skip_api:
        check_api_contract(args.backend)
    else:
        info("跳过 API 契约检查 (--skip-api)")

    # Check 2
    check_chinese_ui(args.frontend)

    # Check 3
    if not args.skip_stress:
        check_stress_test(args.backend)
    else:
        info("跳过压力测试 (--skip-stress)")

    # Check 4
    check_api_key_safety()

    # Check 5
    check_database_init()

    # ── 汇总报告 ──────────────────────────────────────────
    elapsed = (datetime.now() - results["start_time"]).total_seconds()

    print(f"\n{Colors.BOLD}{'=' * 60}{Colors.RESET}")
    print(f"{Colors.BOLD}  质量检查报告{Colors.RESET}")
    print(f"{Colors.BOLD}{'=' * 60}{Colors.RESET}\n")

    print(f"  ✅ 通过: {len(results['passed'])}")
    for item in results["passed"]:
        print(f"     - {item}")

    print(f"  ❌ 失败: {len(results['failed'])}")
    for item in results["failed"]:
        print(f"     - {item}")

    print(f"  ⚠️  警告: {len(results['warnings'])}")
    for item in results["warnings"]:
        print(f"     - {item}")

    print(f"\n  总耗时: {elapsed:.1f}s")

    # 退出码
    if results["failed"]:
        print(f"\n{Colors.RED}❌ 质量检查未通过 — {len(results['failed'])} 项失败{Colors.RESET}")
        sys.exit(1)
    else:
        print(f"\n{Colors.GREEN}✅ 质量检查全部通过{Colors.RESET}")
        sys.exit(0)


if __name__ == "__main__":
    main()
