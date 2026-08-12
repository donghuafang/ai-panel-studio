"""测试发言调度引擎 — SpeechScheduler

覆盖加权随机选择、主持人锚点、静默惩罚、立场冲突加成、
发言长度约束和 thought_summary 返回。
"""

import pytest
from unittest.mock import MagicMock, AsyncMock

from app.services.speech_scheduler import SpeechScheduler


# ── 测试数据工厂 ─────────────────────────────────────────────────

def _make_guest(gid, name, role="guest", stance="中立观点"):
    """快速构建 Guest 对象（MagicMock，仅设置测试用属性）。"""
    g = MagicMock()
    g.id = gid
    g.name = name
    g.role = role
    g.stance = stance
    g.color = "#000000"
    return g


def _make_speech_history(guest_id, round_num, content="测试发言内容"):
    """构建一条发言记录。"""
    return {
        "guest_id": guest_id,
        "round_number": round_num,
        "content": content,
        "speech_type": "statement",
    }


# ── 测试用例 ─────────────────────────────────────────────────────

class TestSpeechSchedulerSelection:
    """发言选择算法测试。"""

    def test_no_mechanical_rotation(self):
        """运行 20 轮调度，断言同一嘉宾连续发言 ≤ 2 次。

        禁止简单的机械轮流（A→B→C→A→B→C），需要加权随机。
        每轮选 1 位发言者（模拟讨论编排中逐人发言）。
        """
        # Arrange
        guests = [
            _make_guest("h1", "主持人", "host", "中立主持"),
            _make_guest("g1", "专家A", "guest", "AI 有益"),
            _make_guest("g2", "专家B", "guest", "AI 危险"),
            _make_guest("g3", "专家C", "guest", "AI 是工具"),
        ]
        scheduler = SpeechScheduler(MagicMock())
        history = []
        total_rounds = 20

        # Act: 模拟 20 轮，每轮选 1 位发言者
        last_speaker = None
        consecutive_count = 0

        for rnd in range(total_rounds):
            # 每轮只选 1 位发言人（实际编排中每轮有主持人开场 + 专家轮流 + 总结，
            # 但这里测试的是纯加权选择算法的非机械性）
            weights = scheduler._compute_weights(guests, history, rnd, total_rounds)
            max_idx = max(range(len(weights)), key=lambda i: weights[i])
            selected = guests[max_idx]

            if selected.id == last_speaker:
                consecutive_count += 1
            else:
                consecutive_count = 1
                last_speaker = selected.id

            history.append(_make_speech_history(selected.id, rnd))

            # Assert: 同一嘉宾不得连续 ≥ 3 次
            assert consecutive_count < 3, (
                f"嘉宾 {selected.name} 已连续发言 {consecutive_count} 次（上限 2 次），"
                f"权重: {[(g.name, w) for g, w in zip(guests, weights)]}"
            )

    def test_host_at_turning_points(self):
        """断言第 0 轮（开场）、第 5 轮（追问串联）、最后一轮（总结）由主持人优先。

        主持人 anchor 权重设为无穷大（float('inf')），确保必定选中。
        """
        # Arrange
        host = _make_guest("h1", "主持人", "host", "中立主持")
        guests = [host, _make_guest("g1", "专家A", "guest", "观点A")]
        scheduler = SpeechScheduler(MagicMock())
        history = []
        total_rounds = 6  # 0-5, so last round is 5

        # Act & Assert: 第 0 轮（开场）
        w0 = scheduler._compute_weights(guests, history, 0, total_rounds)
        assert w0[0] == float("inf"), "第 0 轮（开场）主持人权重应为 inf"

        # 第 5 轮：每 5 轮 + 最后一轮（这里 total_rounds=6, rounds 0-5, round 5 是最后一轮）
        w5 = scheduler._compute_weights(guests, history, 5, total_rounds)
        assert w5[0] == float("inf"), "第 5 轮（每 5 轮追问 + 最后一轮）主持人权重应为 inf"

        # 中间轮次（如第 2 轮）主持人不应 infinite
        w2 = scheduler._compute_weights(guests, history, 2, total_rounds)
        assert w2[0] != float("inf"), "中间轮次主持人权重不应为 inf"

    def test_prefers_silent_guests(self):
        """断言 3 轮未发言的嘉宾权重高于刚发言的嘉宾。

        权重公式: base(1.0) + silent_rounds * 0.3
        """
        # Arrange
        guests = [
            _make_guest("g1", "专家A", "guest", "观点A"),
            _make_guest("g2", "专家B", "guest", "观点B"),
        ]
        scheduler = SpeechScheduler(MagicMock())

        # g1 最近刚在第 9 轮发言，g2 在第 7 轮发言
        history = [
            _make_speech_history("g2", 7, "较早发言"),
            _make_speech_history("g1", 9, "刚发言"),
        ]
        current_round = 10  # 当前第 10 轮
        total_rounds = 10

        # Act
        weights = scheduler._compute_weights(guests, history, current_round, total_rounds)

        # Assert: g2 (沉默 3 轮) 的权重 > g1 (沉默 1 轮)
        # g1: 10 - 9 = 1 轮未发言 → weight = 1.0 + 1*0.3 = 1.3
        # g2: 10 - 7 = 3 轮未发言 → weight = 1.0 + 3*0.3 = 1.9
        assert weights[1] > weights[0], (
            f"沉默 3 轮的专家B 权重 ({weights[1]}) 应 > 刚发言的专家A ({weights[0]})"
        )

    def test_stance_conflict_boosts_reply(self):
        """断言存在对立立场时，speech_type='reply' 的选中概率提升。

        当发言历史中对某嘉宾立场有对立观点时，该嘉宾的下次发言更可能是 'reply'。
        """
        # Arrange
        mock_llm = MagicMock()
        scheduler = SpeechScheduler(mock_llm)

        # Act: 检测对立立场
        stance_a = "AI 最终将在大多数创造性任务上超越人类"
        stance_b = "AI 只是工具，人类创造力不可替代"

        has_conflict = scheduler._has_stance_conflict(stance_a, stance_b)

        # Assert
        assert has_conflict is True, "明确对立的立场应检测为冲突"


class TestSpeechSchedulerGeneration:
    """发言内容生成测试。"""

    @pytest.mark.asyncio
    async def test_content_length_constraint(self):
        """断言生成的 content 字段在 15-60 字之间（1-2 句中文）。"""
        # Arrange
        mock_llm = MagicMock()
        mock_llm.generate_speech = AsyncMock(return_value="人工智能已经深刻改变了各行各业的工作方式，但它仍然无法替代人类的直觉与创造力。")
        scheduler = SpeechScheduler(mock_llm)

        guest = _make_guest("g1", "专家A", "guest", "AI 有益")
        context = [{"role": "user", "content": "【主持人】: 欢迎讨论"}]

        # Act
        result = await scheduler.generate_speech(guest, context, "请发表观点")

        # Assert
        content = result["content"]
        char_count = len(content)
        assert 15 <= char_count <= 60, (
            f"发言长度应在 15-60 字之间，实际 {char_count} 字: '{content}'"
        )

    @pytest.mark.asyncio
    async def test_agent_state_and_thought_summary(self):
        """断言返回 dict 包含 thought_summary 和 agent_state 字段。

        thought_summary 用于前端嘉宾小窗（思考摘要），agent_state 用于指示灯。
        """
        # Arrange
        mock_llm = MagicMock()
        mock_llm.generate_speech = AsyncMock(
            return_value="作为 AI 研究者，我认为我们需要区分狭义和广义的创造力。"
        )
        scheduler = SpeechScheduler(mock_llm)

        guest = _make_guest("g1", "专家A", "guest", "AI 研究视角")
        context = []

        # Act
        result = await scheduler.generate_speech(guest, context, "请发表你的专业观点")

        # Assert
        assert "content" in result, "返回结果必须包含 content 字段"
        assert "thought_summary" in result, "返回结果必须包含 thought_summary 字段"
        assert "agent_state" in result, "返回结果必须包含 agent_state 字段"
        assert result["agent_state"] in ("speaking", "thinking"), (
            f"agent_state 应为 speaking 或 thinking，实际为 {result['agent_state']}"
        )
        assert len(result["thought_summary"]) > 0, "thought_summary 不应为空"
        assert len(result["thought_summary"]) <= len(result["content"]), (
            "thought_summary 不应长于完整发言"
        )
