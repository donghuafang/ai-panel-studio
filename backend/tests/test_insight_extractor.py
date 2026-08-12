"""测试共识与分歧提炼引擎 — InsightExtractor

覆盖 Jaccard 相似度、去重逻辑、共识提炼、分歧检测、
增量更新和短发言跳过。
"""

import json
import pytest
from unittest.mock import MagicMock, AsyncMock

from app.services.insight_extractor import InsightExtractor


# ── 测试数据工厂 ─────────────────────────────────────────────────

def _make_speech(guest_id, content, round_number=1):
    """构建一条发言记录。"""
    return {"guest_id": guest_id, "content": content, "round_number": round_number}


def _make_guest(gid, name, stance="中立"):
    """构建一个嘉宾对象。"""
    return {"id": gid, "name": name, "stance": stance}


# ── Jaccard 相似度 & 基础逻辑测试（纯计算，无需 Mock） ──────────

class TestInsightExtractorJaccard:
    """Jaccard 相似度与去重逻辑。"""

    def test_jaccard_similarity_threshold(self):
        """断言两条高度相似的文本 Jaccard > 0.7，不相关文本 < 0.3。"""
        extractor = InsightExtractor(MagicMock())

        text_a = "AI 将大幅提升编程效率"
        text_b = "AI 将大幅提升编程效率和质量"
        text_c = "人类创造力是 AI 无法替代的核心优势"

        sim_ab = extractor.jaccard_similarity(text_a, text_b)
        sim_ac = extractor.jaccard_similarity(text_a, text_c)

        assert sim_ab > 0.7, f"高度相似文本 Jaccard 应 > 0.7，实际 {sim_ab:.3f}"
        assert sim_ac < 0.3, f"不相关文本 Jaccard 应 < 0.3，实际 {sim_ac:.3f}"

    def test_jaccard_identical_strings(self):
        """完全相同的字符串 Jaccard 相似度应为 1.0。"""
        extractor = InsightExtractor(MagicMock())

        text = "AI 是强大的辅助工具但不是替代品"
        sim = extractor.jaccard_similarity(text, text)

        assert sim == 1.0, f"相同文本 Jaccard 应为 1.0，实际 {sim}"

    def test_jaccard_empty_string(self):
        """空字符串的 Jaccard 相似度应为 0.0。"""
        extractor = InsightExtractor(MagicMock())

        assert extractor.jaccard_similarity("", "测试") == 0.0
        assert extractor.jaccard_similarity("测试", "") == 0.0
        assert extractor.jaccard_similarity("", "") == 0.0

    def test_is_duplicate_detection(self):
        """is_duplicate 应在 Jaccard > 0.5 或关键词重叠 > 60% 时返回 True。"""
        extractor = InsightExtractor(MagicMock())

        existing = [
            {"id": "c1", "content": "AI 将大幅提升编程效率"},
            {"id": "c2", "content": "人类创造力是核心优势"},
        ]

        # 高度相似的 content → duplicate
        assert extractor.is_duplicate("AI 将显著提升编程效率", existing) is True

        # 全新的 content → not duplicate
        assert extractor.is_duplicate("数据隐私是最重要的伦理问题", existing) is False

    def test_should_extract(self):
        """≥ 3 条发言才触发提炼，≤ 2 条返回空。"""
        extractor = InsightExtractor(MagicMock())

        assert extractor.should_extract(0) is False
        assert extractor.should_extract(1) is False
        assert extractor.should_extract(2) is False
        assert extractor.should_extract(3) is True
        assert extractor.should_extract(5) is True
        assert extractor.should_extract(20) is True


# ── 共识提炼测试（Mock LLM）─────────────────────────────────────

class TestInsightExtractorConsensus:
    """共识提炼相关。"""

    @pytest.mark.asyncio
    async def test_extract_consensus_from_agreements(self):
        """多条认同性发言 → 返回 1 条共识，supporter_guest_ids 覆盖所有发言者。"""
        # Arrange
        mock_llm = MagicMock()
        mock_llm.chat_completion = AsyncMock(return_value=(
            '[{"content": "AI 是强大的辅助工具，能提升工作效率",'
            '"supporter_guest_ids": ["g1", "g2", "g3"]}]'
        ))
        extractor = InsightExtractor(mock_llm)

        speeches = [
            _make_speech("g1", "AI 是强大的辅助工具，我们应该善用"),
            _make_speech("g2", "我同意，AI 帮助人类更高效工作"),
            _make_speech("g3", "没错，AI 作为工具确实能提升效率"),
        ]
        guests = [
            _make_guest("g1", "专家A", "AI 有益"),
            _make_guest("g2", "专家B", "AI 是工具"),
            _make_guest("g3", "专家C", "AI 辅助人类"),
        ]

        # Act
        result = await extractor.extract_consensus(speeches, guests, [])

        # Assert
        assert len(result) == 1, f"期望 1 条共识，实际 {len(result)}"
        assert result[0]["type"] == "consensus"
        assert set(result[0]["supporter_guest_ids"]) == {"g1", "g2", "g3"}, (
            f"supporter_guest_ids 应包含所有发言者"
        )

    @pytest.mark.asyncio
    async def test_consensus_deduplication(self):
        """连续 2 次提炼包含相似内容时，第 2 次不生成重复共识。"""
        # Arrange
        mock_llm = MagicMock()
        mock_llm.chat_completion = AsyncMock()
        extractor = InsightExtractor(mock_llm)

        speeches_round1 = [
            _make_speech("g1", "AI 是强大的辅助工具"),
            _make_speech("g2", "AI 帮助人类更高效工作"),
            _make_speech("g3", "AI 确实能提升效率"),
        ]
        guests = [
            _make_guest("g1", "专家A"),
            _make_guest("g2", "专家B"),
            _make_guest("g3", "专家C"),
        ]

        # 第一次提炼 → 返回 1 条共识
        mock_llm.chat_completion.return_value = (
            '[{"content": "AI 是强大的辅助工具", "supporter_guest_ids": ["g1", "g2", "g3"]}]'
        )
        existing = await extractor.extract_consensus(speeches_round1, guests, [])

        # 第二次提炼 → LLM 返回相同内容，但应被去重过滤
        mock_llm.chat_completion.return_value = (
            '[{"content": "AI 是强大的辅助工具能提升效率", "supporter_guest_ids": ["g1", "g2"]}]'
        )
        speeches_round2 = speeches_round1 + [_make_speech("g1", "AI 持续辅助人类工作")]
        new_result = await extractor.extract_consensus(speeches_round2, guests, existing)

        # Assert: 新增结果中不应包含与已有共识重复的条目
        assert len(new_result) == 0, (
            f"去重后应无新增共识（Jaccard 相似度过高），实际新增 {len(new_result)} 条"
        )

    @pytest.mark.asyncio
    async def test_incremental_update_not_overwrite(self):
        """增量提炼时已有共识的 id 不变，只追加新条目。"""
        # Arrange
        mock_llm = MagicMock()
        mock_llm.chat_completion = AsyncMock()
        extractor = InsightExtractor(mock_llm)

        speeches = [
            _make_speech("g1", "AI 提升编程效率"),
            _make_speech("g2", "AI 辅助设计工作"),
            _make_speech("g3", "AI 加速数据分析"),
        ]
        guests = [
            _make_guest("g1", "专家A"),
            _make_guest("g2", "专家B"),
            _make_guest("g3", "专家C"),
        ]

        # 第一次提炼 → 2 条共识
        mock_llm.chat_completion.return_value = (
            '[{"content": "AI 提升工作效率", "supporter_guest_ids": ["g1", "g3"]},'
            '{"content": "AI 改变工作方式", "supporter_guest_ids": ["g2"]}]'
        )
        existing = await extractor.extract_consensus(speeches, guests, [])

        assert len(existing) == 2
        old_ids = [c["id"] for c in existing]
        first_consensus_content = existing[0]["content"]

        # 第二次提炼（增量）→ 返回 1 条新共识，旧共识 id 不变
        mock_llm.chat_completion.return_value = (
            '[{"content": "数据安全是重要议题", "supporter_guest_ids": ["g1", "g2"]}]'
        )
        new_speeches = speeches + [_make_speech("g2", "数据安全也需要关注")]
        merged = await extractor.extract_consensus(new_speeches, guests, existing)

        # Assert: 旧共识 id 不变
        assert existing[0]["id"] == old_ids[0], "已有共识 id 不应改变"
        assert existing[0]["content"] == first_consensus_content, "已有共识内容不应改变"
        # 总共识数增加到 3
        assert len(existing) == 3, f"期望 3 条共识（2 旧 + 1 新），实际 {len(existing)}"


# ── 分歧提炼测试（Mock LLM）─────────────────────────────────────

class TestInsightExtractorDivergence:
    """分歧检测相关。"""

    @pytest.mark.asyncio
    async def test_extract_divergence_from_opposing(self):
        """"A 好" vs "A 不好" 的发言 → 1 条分歧，opposing_pairs 包含对立双方。"""
        # Arrange
        mock_llm = MagicMock()
        mock_llm.chat_completion = AsyncMock(return_value=(
            '[{"content": "关于 AI 是否会取代人类的观点分歧",'
            '"opposing_pairs": [["g1", "g2"]],'
            '"side_a": "AI 将超越人类",'
            '"side_b": "AI 只是工具"}]'
        ))
        extractor = InsightExtractor(mock_llm)

        speeches = [
            _make_speech("g1", "AI 最终将在大多数创造性任务上超越人类"),
            _make_speech("g2", "AI 只是工具，人类创造力不可替代"),
            _make_speech("g3", "我们需要更多数据才能判断"),
        ]
        guests = [
            _make_guest("g1", "乐观派", "AI 将超越人类"),
            _make_guest("g2", "保守派", "AI 只是工具"),
            _make_guest("g3", "中立派", "需要更多研究"),
        ]

        # Act
        result = await extractor.extract_divergence(speeches, guests, [])

        # Assert
        assert len(result) == 1, f"期望 1 条分歧，实际 {len(result)}"
        assert result[0]["type"] == "divergence"
        assert ["g1", "g2"] in result[0]["opposing_pairs"] or \
               ["g2", "g1"] in result[0]["opposing_pairs"], (
            f"opposing_pairs 应包含 g1 和 g2"
        )

    @pytest.mark.asyncio
    async def test_extract_empty_on_short_transcript(self):
        """≤ 2 条发言时 extract_consensus / extract_divergence 均返回空列表。"""
        # Arrange
        extractor = InsightExtractor(MagicMock())

        short_speeches = [
            _make_speech("g1", "AI 很有用"),
            _make_speech("g2", "我同意"),
        ]
        guests = [_make_guest("g1", "A"), _make_guest("g2", "B")]

        # Act
        consensus = await extractor.extract_consensus(short_speeches, guests, [])
        divergence = await extractor.extract_divergence(short_speeches, guests, [])

        # Assert
        assert consensus == [], f"≤2 条发言不应提炼共识，实际返回 {len(consensus)} 条"
        assert divergence == [], f"≤2 条发言不应提炼分歧，实际返回 {len(divergence)} 条"


# ── JSON 解析容错测试 ──────────────────────────────────────────

class TestInsightExtractorParsing:
    """LLM 返回格式容错。"""

    @pytest.mark.asyncio
    async def test_parse_json_embedded_in_text(self):
        """LLM 返回的 JSON 数组嵌入在说明文本中时，应能提取并解析。"""
        # Arrange
        mock_llm = MagicMock()
        mock_llm.chat_completion = AsyncMock(return_value=(
            "好的，以下是新发现的共识：\n"
            '[{"content": "AI 提升工作效率", "supporter_guest_ids": ["g1", "g2"]}]\n'
            "以上是本次提炼结果。"
        ))
        extractor = InsightExtractor(mock_llm)

        speeches = [
            _make_speech("g1", "AI 提升编程效率"),
            _make_speech("g2", "AI 加速数据处理"),
            _make_speech("g3", "AI 优化工作流程"),
        ]
        guests = [_make_guest("g1", "A"), _make_guest("g2", "B"), _make_guest("g3", "C")]

        # Act
        result = await extractor.extract_consensus(speeches, guests, [])

        # Assert: 应成功提取嵌入的 JSON
        assert len(result) == 1, f"应提取到 1 条共识，实际 {len(result)}"
        assert "效率" in result[0]["content"]

    @pytest.mark.asyncio
    async def test_parse_completely_invalid_json(self):
        """LLM 返回完全无法解析的内容时，应安全返回空列表。"""
        # Arrange
        mock_llm = MagicMock()
        mock_llm.chat_completion = AsyncMock(return_value="抱歉，我无法分析这些发言。")
        extractor = InsightExtractor(mock_llm)

        speeches = [
            _make_speech("g1", "AI 提升编程效率"),
            _make_speech("g2", "AI 加速数据处理"),
            _make_speech("g3", "AI 优化工作流程"),
        ]
        guests = [_make_guest("g1", "A"), _make_guest("g2", "B"), _make_guest("g3", "C")]

        # Act
        result = await extractor.extract_consensus(speeches, guests, [])

        # Assert
        assert result == [], f"无效 JSON 应返回空列表，实际 {len(result)} 条"

    @pytest.mark.asyncio
    async def test_parse_single_object_not_array(self):
        """LLM 返回单个对象（非数组）时，应自动包装为列表处理。"""
        # Arrange
        mock_llm = MagicMock()
        mock_llm.chat_completion = AsyncMock(return_value=(
            '{"content": "AI是辅助工具", "supporter_guest_ids": ["g1", "g2"]}'
        ))
        extractor = InsightExtractor(mock_llm)

        speeches = [
            _make_speech("g1", "AI 是强大的辅助工具"),
            _make_speech("g2", "AI 帮助人类更高效工作"),
            _make_speech("g3", "AI 提升效率"),
        ]
        guests = [_make_guest("g1", "A"), _make_guest("g2", "B"), _make_guest("g3", "C")]

        # Act
        result = await extractor.extract_consensus(speeches, guests, [])

        # Assert
        assert len(result) == 1, f"单个对象应被包装为列表，实际 {len(result)} 条"

    @pytest.mark.asyncio
    async def test_divergence_json_embedded_in_text(self):
        """分歧提炼：JSON 嵌入在说明文本中时也能正确提取。"""
        # Arrange
        mock_llm = MagicMock()
        mock_llm.chat_completion = AsyncMock(return_value=(
            "分析发现以下分歧：\n"
            '[{"content": "关于AI风险的争议", "opposing_pairs": [["g1", "g2"]],'
            '"side_a": "AI安全可控", "side_b": "AI有风险"}]'
        ))
        extractor = InsightExtractor(mock_llm)

        speeches = [
            _make_speech("g1", "AI 是安全可控的"),
            _make_speech("g2", "AI 存在不可控风险"),
            _make_speech("g3", "需要更多研究"),
        ]
        guests = [_make_guest("g1", "A"), _make_guest("g2", "B"), _make_guest("g3", "C")]

        # Act
        result = await extractor.extract_divergence(speeches, guests, [])

        # Assert
        assert len(result) == 1, f"应提取到 1 条分歧，实际 {len(result)}"
        assert result[0]["side_a"] == "AI安全可控"

    @pytest.mark.asyncio
    async def test_skip_items_with_empty_content(self):
        """LLM 返回的条目中 content 为空字符串时应跳过。"""
        # Arrange
        mock_llm = MagicMock()
        mock_llm.chat_completion = AsyncMock(return_value=json.dumps([
            {"content": "", "supporter_guest_ids": ["g1"]},
            {"content": "有效的共识内容", "supporter_guest_ids": ["g2", "g3"]},
            {"content": "   ", "supporter_guest_ids": ["g1"]},
        ]))
        extractor = InsightExtractor(mock_llm)

        speeches = [
            _make_speech("g1", "AI 提升编程效率"),
            _make_speech("g2", "AI 加速数据处理"),
            _make_speech("g3", "AI 优化工作流程"),
        ]
        guests = [_make_guest("g1", "A"), _make_guest("g2", "B"), _make_guest("g3", "C")]

        # Act
        result = await extractor.extract_consensus(speeches, guests, [])

        # Assert: 空 content 的项被跳过，只保留有效项
        assert len(result) == 1, f"应只保留 1 条有效共识，实际 {len(result)}"
        assert result[0]["content"] == "有效的共识内容"
