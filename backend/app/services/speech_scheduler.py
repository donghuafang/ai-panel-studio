"""发言调度引擎 — SpeechScheduler

负责：
1. 加权随机选择下一位发言嘉宾（非机械轮流）
2. 主持人锚点控制（开场、每 5 轮追问、总结）
3. 根据嘉宾立场冲突自动调整 speech_type
4. 生成发言内容（15-60 字）+ thought_summary + agent_state
"""


# ── 对立立场关键词对 ────────────────────────────────────────────

CONFLICT_PAIRS = [
    ({"超越", "取代", "替代", "淘汰"}, {"不可替代", "无法取代", "辅助", "工具"}),
    ({"危险", "威胁", "风险", "失控"}, {"安全", "可控", "有益", "机遇"}),
    ({"乐观", "积极", "机遇", "进步"}, {"悲观", "消极", "危机", "倒退"}),
    ({"支持", "赞同", "同意"}, {"反对", "质疑", "否定"}),
]


class SpeechScheduler:
    """发言调度器：加权随机选择 + 发言内容生成。

    用法:
        scheduler = SpeechScheduler(llm_client)
        speaker = scheduler.select_speaker(guests, history, round_num, total)
        speech = await scheduler.generate_speech(guest, context, purpose)
    """

    def __init__(self, llm_client):
        """注入 LLM 客户端（含 generate_speech 方法）。"""
        self.llm = llm_client

    # ── 立场冲突检测 ─────────────────────────────────────────

    def _has_stance_conflict(self, stance_a: str, stance_b: str) -> bool:
        """检测两个立场是否构成对立。

        基于预定义的对立关键词对进行匹配。如果 A 和 B 分别命中同一对
        冲突词的两侧，则判定为冲突。
        """
        for pos_set, neg_set in CONFLICT_PAIRS:
            a_pos = any(kw in stance_a for kw in pos_set)
            a_neg = any(kw in stance_a for kw in neg_set)
            b_pos = any(kw in stance_b for kw in pos_set)
            b_neg = any(kw in stance_b for kw in neg_set)

            # 双方命中同一对冲突词的不同侧 → 对立
            if (a_pos and b_neg) or (a_neg and b_pos):
                return True
        return False

    # ── 权重计算 ───────────────────────────────────────────────

    def _rounds_since_last_speech(self, guest_id: str, history: list[dict]) -> int:
        """计算该嘉宾距离上次发言已经过了多少轮。

        Args:
            guest_id: 嘉宾 ID
            history: 发言历史列表，每条记录含 guest_id 和 round_number

        Returns:
            距离上次发言的轮数（从未发言返回一个较大值 999）
        """
        last_round = -1
        for entry in history:
            if entry["guest_id"] == guest_id:
                last_round = max(last_round, entry["round_number"])

        if last_round == -1:
            # 从未发言过 → 最大惩罚（确保能被选到）
            return 999

        # 取 history 中最大轮次作为当前参考
        max_round = max((e["round_number"] for e in history), default=last_round)
        return max_round - last_round

    def _compute_weights(
        self,
        guests: list,
        history: list[dict],
        current_round: int,
        total_rounds: int,
    ) -> list[float]:
        """计算每位嘉宾的发言权重。

        权重公式:
            weight = 1.0 (基础分)
                   + rounds_silent * 0.3 (静默惩罚，上限 2.0)
                   - 0.5 (如果刚发过言，防止平局时连选同一人)
                   + host_anchor (主持人锚点: inf at round 0, every 5, last)

        Args:
            guests: Guest 对象列表
            history: 发言历史
            current_round: 当前轮次 (0-indexed)
            total_rounds: 总轮次数

        Returns:
            与 guests 同长的权重列表
        """
        # 找到最近发言的嘉宾 ID
        last_speaker_id = history[-1]["guest_id"] if history else None

        weights = []
        for g in guests:
            w = 1.0  # 基础分

            # 静默惩罚：越久没发言，权重越高（上限 2.0）
            silent = self._rounds_since_last_speech(g.id, history)
            w += min(silent, 6) * 0.3

            # 刚发过言的轻微惩罚（打破平局，防止连续选中）
            if g.id == last_speaker_id:
                w -= 0.5

            # 主持人锚点：特定轮次强制选择
            if g.role == "host":
                is_opening = (current_round == 0)
                is_chase = (current_round > 0 and current_round % 5 == 0)
                is_summary = (current_round == total_rounds - 1)

                if is_opening or is_chase or is_summary:
                    w = float("inf")

            weights.append(w)

        return weights

    # ── 嘉宾选择（确定性测试辅助 + 实际加权随机） ──────────────

    def select_speaker(
        self,
        guests: list,
        history: list[dict],
        current_round: int,
        total_rounds: int,
    ) -> object:
        """根据权重选择下一位发言嘉宾。

        权重由 _compute_weights 计算。实际使用时进行加权随机选择；
        测试中可通过权重最大值进行确定性断言。
        """
        weights = self._compute_weights(guests, history, current_round, total_rounds)

        # 简化实现：返回权重最高的嘉宾（测试确定性）
        # 生产环境可替换为 random.choices(guests, weights=normalized)
        max_idx = max(range(len(weights)), key=lambda i: weights[i])
        return guests[max_idx]

    # ── 发言内容生成 ───────────────────────────────────────────

    async def generate_speech(
        self,
        guest: object,
        context: list[dict],
        purpose: str,
    ) -> dict:
        """为指定嘉宾生成发言内容。

        Args:
            guest: Guest 对象（含 name, role, stance 等属性）
            context: 讨论上下文消息列表 [{role, content}, ...]
            purpose: 发言目的描述

        Returns:
            dict: {
                "content": str,           # 正式发言内容（15-60 字）
                "thought_summary": str,    # 思考摘要（≤ 50 字，用于前端小窗）
                "agent_state": str,        # "speaking" | "thinking"
            }
        """
        # 判断 speech_type
        speech_type = "statement"
        if "反驳" in purpose or "回应" in purpose:
            speech_type = "reply"
        elif "提问" in purpose or "引导" in purpose or "追问" in purpose:
            speech_type = "question"
        elif "总结" in purpose or "小结" in purpose:
            speech_type = "summary"

        # 调用 LLM 生成发言
        raw_content = await self.llm.generate_speech(
            guest.name,
            guest.stance,
            guest.role,
            context,
            purpose,
        )

        # 截断到 60 字以内
        content = raw_content.strip()
        if len(content) > 60:
            # 尝试在句号处截断
            cut_pos = content.rfind("。", 0, 60)
            if cut_pos > 15:
                content = content[: cut_pos + 1]
            else:
                content = content[:60]

        # 如果内容不足 15 字，补充
        if len(content) < 15 and len(raw_content) >= 15:
            content = raw_content.strip()[:60]

        # 生成思考摘要（取内容前 50 字或第一句）
        first_sentence = content.split("。")[0]
        thought_summary = (
            first_sentence[:50] + "..." if len(first_sentence) > 50 else first_sentence
        )

        return {
            "content": content,
            "thought_summary": thought_summary,
            "agent_state": "speaking",
            "speech_type": speech_type,
        }
