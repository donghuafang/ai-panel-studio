"""测试嘉宾生成服务 — GuestGenerator

所有 LLM 调用通过 mock_llm_client 模拟，零真实 API 消耗。
"""

import os
import asyncio
import pytest
from unittest.mock import patch, MagicMock, AsyncMock

from app.services.guest_generator import GuestGenerator, COLOR_POOL


# ── 测试数据工厂 ─────────────────────────────────────────────────

def _mock_guests_response(expert_count=3):
    """构建 mock LLM 返回的标准嘉宾列表。

    第一位必为主持人，其余为专家。立场包含"AI"关键词以通过话题相关性测试。
    """
    guests = [
        {
            "name": "张明",
            "profession": "科技媒体主编",
            "title": "资深科技评论员",
            "stance": "作为中立主持人，致力于引导各方探讨 AI 对创造力的影响",
            "color": "#4A90D9",
            "role": "host",
        }
    ]
    expert_names = ["李伟", "王芳", "赵强", "陈静", "刘洋", "黄磊", "周敏", "吴昊"]
    expert_colors = ["#FF6B6B", "#4ECDC4", "#45B7D1", "#96CEB4",
                     "#FFEAA7", "#DDA0DD", "#F7DC6F", "#FF8A5C"]
    professions = ["软件工程师", "AI 研究员", "企业家", "设计师",
                   "教育家", "数据科学家", "产品经理", "投资人"]

    for i in range(expert_count):
        guests.append({
            "name": expert_names[i],
            "profession": professions[i],
            "title": f"资深{professions[i]}",
            "stance": f"关于 AI 与创造力的观点立场 {i+1}：从{professions[i]}角度出发",
            "color": expert_colors[i],
            "role": "guest",
        })
    return guests


# ── 测试用例 ─────────────────────────────────────────────────────

class TestGuestGenerator:
    """嘉宾生成器单元测试（全部 Mock LLM）。"""

    @pytest.fixture(autouse=True)
    def _set_api_key(self):
        """所有测试自动设置一个模拟 API Key，避免校验失败。"""
        with patch.dict(os.environ, {"DEEPSEEK_API_KEY": "sk-test-mock"}, clear=False):
            yield

    @pytest.mark.asyncio
    async def test_generate_guests_creates_host_first(self, mock_llm_client):
        """断言生成结果中第一条角色为 host，且只有 1 个主持人。"""
        # Arrange
        mock_llm_client.generate_guests.return_value = _mock_guests_response(3)
        generator = GuestGenerator(mock_llm_client)

        # Act
        result = await generator.generate("AI 测试话题", 3)

        # Assert
        assert result[0]["role"] == "host", "第一条必须是主持人"
        host_count = sum(1 for g in result if g["role"] == "host")
        assert host_count == 1, f"应有且仅有 1 个主持人，实际 {host_count} 个"

    @pytest.mark.asyncio
    async def test_generate_guests_respects_count(self, mock_llm_client):
        """传入 guest_count=4，断言返回 5 人（1 host + 4 guest）。"""
        # Arrange
        mock_llm_client.generate_guests.return_value = _mock_guests_response(4)
        generator = GuestGenerator(mock_llm_client)

        # Act
        result = await generator.generate("测试话题", 4)

        # Assert
        assert len(result) == 5, f"期望 5 人（1 host + 4 guest），实际 {len(result)} 人"

    @pytest.mark.asyncio
    async def test_generate_guests_color_unique(self, mock_llm_client):
        """断言所有嘉宾的 color 字段互不相同。"""
        # Arrange: mock 返回无颜色字段的数据，依赖 _assign_colors 填充
        guests_no_color = [
            {"name": "张三", "profession": "主持", "title": "主编", "stance": "中立", "color": "", "role": "host"},
            {"name": "李四", "profession": "工程师", "title": "开发", "stance": "观点A", "color": "", "role": "guest"},
            {"name": "王五", "profession": "研究员", "title": "博士", "stance": "观点B", "color": "", "role": "guest"},
        ]
        mock_llm_client.generate_guests.return_value = guests_no_color
        generator = GuestGenerator(mock_llm_client)

        # Act
        result = await generator.generate("测试", 2)

        # Assert
        colors = [g["color"] for g in result]
        assert len(colors) == len(set(colors)), f"颜色必须互不相同，实际: {colors}"

    @pytest.mark.asyncio
    async def test_generate_guests_stance_related_to_topic(self, mock_llm_client):
        """Mock LLM 返回含"AI"关键词的 stance，断言立场中包含话题关键词。"""
        # Arrange
        mock_llm_client.generate_guests.return_value = _mock_guests_response(3)
        generator = GuestGenerator(mock_llm_client)

        # Act
        result = await generator.generate("AI 与创造力", 3)

        # Assert
        for guest in result:
            assert "AI" in guest["stance"], (
                f"{guest['name']} 的 stance 中应包含话题关键词 'AI'"
            )

    def test_generate_guests_invalid_count_raises(self):
        """传入 guest_count=1 或 =9，断言抛出 ValueError。"""
        generator = GuestGenerator(MagicMock())

        with pytest.raises(ValueError, match="2-8"):
            generator.validate_count(1)
        with pytest.raises(ValueError, match="2-8"):
            generator.validate_count(9)

    @patch.dict(os.environ, {"DEEPSEEK_API_KEY": ""}, clear=True)
    def test_generate_guests_api_key_missing_raises(self):
        """模拟环境变量为空，断言抛出 RuntimeError。"""
        generator = GuestGenerator(MagicMock())

        with pytest.raises(RuntimeError, match="DEEPSEEK_API_KEY"):
            generator.validate_api_key()

    @pytest.mark.asyncio
    async def test_generate_retries_on_validation_error(self):
        """LLM 首次返回无效数据时自动重试，耗尽后抛出异常。

        覆盖 generate() 内部的 host-first 校验、count 校验和重试循环。
        """
        # Arrange: LLM 持续返回缺少主持人的数据
        mock_llm = MagicMock()
        mock_llm.generate_guests = AsyncMock(return_value=[
            {"name": "专家A", "role": "guest", "stance": "AI 观点", "color": "", "profession": "工程师", "title": "专家"},
            {"name": "专家B", "role": "guest", "stance": "AI 观点", "color": "", "profession": "研究员", "title": "专家"},
            {"name": "专家C", "role": "guest", "stance": "AI 观点", "color": "", "profession": "设计师", "title": "专家"},
        ])
        generator = GuestGenerator(mock_llm)

        # Patch asyncio.sleep 避免测试中真等待
        with patch.dict(os.environ, {"DEEPSEEK_API_KEY": "sk-test"}, clear=False):
            with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
                # Act & Assert: 3 次尝试后仍无效，抛出异常
                with pytest.raises(ValueError, match="role='host'"):
                    await generator.generate("AI 测试话题", 2)

                # 断言重试了 2 次（总共 3 次尝试）
                assert mock_llm.generate_guests.call_count == 3
                assert mock_sleep.call_count == 2  # 前 2 次失败后各 sleep 一次


