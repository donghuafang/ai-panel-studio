"""共识与分歧提炼引擎 — InsightExtractor

负责：
1. 从讨论发言中增量提炼共识（supporter_guest_ids）
2. 检测观点分歧（opposing_pairs）
3. 基于 Jaccard 相似度的共识去重
4. 短发言跳过（≤ 2 条不提炼）
"""

import json


class InsightExtractor:
    """共识与分歧提炼器：增量分析 + 去重。

    用法:
        extractor = InsightExtractor(llm_client)
        consensus = await extractor.extract_consensus(speeches, guests, existing)
        divergence = await extractor.extract_divergence(speeches, guests, existing)
    """

    def __init__(self, llm_client):
        """注入 LLM 客户端（含 chat_completion 方法）。

        Args:
            llm_client: 实现了 chat_completion(prompt) -> str 的对象
        """
        self.llm = llm_client
        self._consensus_counter = 0
        self._divergence_counter = 0

    # ── Jaccard 相似度（基于字符 bigram） ──────────────────────

    def jaccard_similarity(self, text_a: str, text_b: str) -> float:
        """计算两个文本的 Jaccard 相似度。

        基于字符 bigram（相邻字符对）构建集合，计算交集/并集比值。
        对于中文文本，字符 bigram 比词级分词更稳定、无外部依赖。

        Args:
            text_a: 文本 A
            text_b: 文本 B

        Returns:
            float: Jaccard 相似度 [0.0, 1.0]
        """
        if not text_a and not text_b:
            return 0.0
        if not text_a or not text_b:
            return 0.0

        def bigrams(s: str) -> set[str]:
            return {s[i : i + 2] for i in range(len(s) - 1)} if len(s) >= 2 else {s}

        set_a = bigrams(text_a)
        set_b = bigrams(text_b)

        intersection = set_a & set_b
        union = set_a | set_b

        if not union:
            return 0.0

        return len(intersection) / len(union)

    # ── 去重逻辑 ──────────────────────────────────────────────

    def is_duplicate(self, new_content: str, existing: list[dict]) -> bool:
        """判断新内容是否与已有共识/分歧重复。

        规则：对任意已有条目，若 Jaccard 相似度 > 0.5，视为重复。

        Args:
            new_content: 待检查的新内容文本
            existing: 已有共识/分歧列表（每项含 content 字段）

        Returns:
            bool: True 表示与已有条目重复，应跳过
        """
        for item in existing:
            sim = self.jaccard_similarity(new_content, item.get("content", ""))
            if sim > 0.5:
                return True
        return False

    # ── 提炼触发条件 ──────────────────────────────────────────

    def should_extract(self, speech_count: int) -> bool:
        """判断是否应该触发提炼（≥ 3 条发言）。"""
        return speech_count >= 3

    # ── 共识提炼 ──────────────────────────────────────────────

    async def extract_consensus(
        self,
        recent_speeches: list[dict],
        all_guests: list[dict],
        existing_consensus: list[dict],
    ) -> list[dict]:
        """从最近发言中增量提炼共识。

        Args:
            recent_speeches: 最近发言列表 [{guest_id, content, round_number}, ...]
            all_guests: 所有嘉宾 [{id, name, stance}, ...]
            existing_consensus: 当前已有的共识列表（会被原地追加新条目）

        Returns:
            list[dict]: 本次新增的共识条目（不含已有）
        """
        if not self.should_extract(len(recent_speeches)):
            return []

        # 构建嘉宾映射
        guest_map = {g["id"]: g["name"] for g in all_guests}

        # 构建提示语
        speeches_text = "\n".join(
            f"- {guest_map.get(s['guest_id'], s['guest_id'])}：{s['content']}"
            for s in recent_speeches
        )
        existing_text = "\n".join(
            f"- {c['content']}" for c in existing_consensus
        ) if existing_consensus else "（无已有共识）"

        prompt = (
            f"你是一场圆桌讨论的洞察提炼助手。请从以下发言中提炼出嘉宾之间达成的共识。\n\n"
            f"【讨论发言】\n{speeches_text}\n\n"
            f"【已有共识】\n{existing_text}\n\n"
            f"请以 JSON 数组格式返回新发现的共识（不要重复已有共识），"
            f"每项含 content（共识内容，≤ 50 字）和 supporter_guest_ids（支持该共识的嘉宾 ID 列表）。"
            f"如果未发现新共识，返回空数组 []。\n"
            f'格式示例：[{{"content": "...", "supporter_guest_ids": ["g1", "g2"]}}]'
        )

        # 调用 LLM
        raw = await self.llm.chat_completion(prompt)
        return self._parse_consensus_response(raw, existing_consensus)

    def _parse_consensus_response(
        self, raw: str, existing: list[dict]
    ) -> list[dict]:
        """解析 LLM 返回的共识 JSON 并去重。

        Args:
            raw: LLM 原始返回文本
            existing: 已有共识列表（原地追加新条目）

        Returns:
            list[dict]: 本次新增的共识条目
        """
        try:
            items = json.loads(raw)
            if not isinstance(items, list):
                items = [items]
        except json.JSONDecodeError:
            # 尝试提取 JSON 数组
            start = raw.find("[")
            end = raw.rfind("]")
            if start != -1 and end != -1 and end > start:
                try:
                    items = json.loads(raw[start : end + 1])
                except json.JSONDecodeError:
                    return []
            else:
                return []

        new_items = []
        for item in items:
            content = item.get("content", "").strip()
            if not content:
                continue

            # 去重
            if self.is_duplicate(content, existing):
                continue

            # 生成 ID 并追加
            self._consensus_counter += 1
            entry = {
                "id": f"consensus_{self._consensus_counter}",
                "type": "consensus",
                "content": content,
                "supporter_guest_ids": item.get("supporter_guest_ids", []),
            }
            existing.append(entry)
            new_items.append(entry)

        return new_items

    # ── 分歧提炼 ──────────────────────────────────────────────

    async def extract_divergence(
        self,
        recent_speeches: list[dict],
        all_guests: list[dict],
        existing_divergence: list[dict],
    ) -> list[dict]:
        """从最近发言中增量提炼观点分歧。

        Args:
            recent_speeches: 最近发言列表 [{guest_id, content, round_number}, ...]
            all_guests: 所有嘉宾 [{id, name, stance}, ...]
            existing_divergence: 当前已有的分歧列表（会被原地追加新条目）

        Returns:
            list[dict]: 本次新增的分歧条目（不含已有）
        """
        if not self.should_extract(len(recent_speeches)):
            return []

        # 构建嘉宾映射
        guest_map = {g["id"]: g["name"] for g in all_guests}

        # 构建提示语
        speeches_text = "\n".join(
            f"- {guest_map.get(s['guest_id'], s['guest_id'])}：{s['content']}"
            for s in recent_speeches
        )
        existing_text = "\n".join(
            f"- {d['content']}" for d in existing_divergence
        ) if existing_divergence else "（无已有分歧）"

        prompt = (
            f"你是一场圆桌讨论的洞察提炼助手。请从以下发言中识别嘉宾之间的观点分歧。\n\n"
            f"【讨论发言】\n{speeches_text}\n\n"
            f"【已有分歧】\n{existing_text}\n\n"
            f"请以 JSON 数组格式返回新发现的分歧（不要重复已有分歧），每项含：\n"
            f"- content：分歧内容描述（≤ 50 字）\n"
            f"- opposing_pairs：对立嘉宾 ID 对列表，如 [[\"g1\", \"g2\"]]\n"
            f"- side_a：正方观点简述\n"
            f"- side_b：反方观点简述\n"
            f"如果未发现新分歧，返回空数组 []。\n"
            f'格式示例：[{{"content": "关于AI风险的争议",'
            f'"opposing_pairs": [["g1", "g2"]], "side_a": "AI安全可控", "side_b": "AI存在不可控风险"}}]'
        )

        # 调用 LLM
        raw = await self.llm.chat_completion(prompt)
        return self._parse_divergence_response(raw, existing_divergence)

    def _parse_divergence_response(
        self, raw: str, existing: list[dict]
    ) -> list[dict]:
        """解析 LLM 返回的分歧 JSON 并去重。

        Args:
            raw: LLM 原始返回文本
            existing: 已有分歧列表（原地追加新条目）

        Returns:
            list[dict]: 本次新增的分歧条目
        """
        try:
            items = json.loads(raw)
            if not isinstance(items, list):
                items = [items]
        except json.JSONDecodeError:
            start = raw.find("[")
            end = raw.rfind("]")
            if start != -1 and end != -1 and end > start:
                try:
                    items = json.loads(raw[start : end + 1])
                except json.JSONDecodeError:
                    return []
            else:
                return []

        new_items = []
        for item in items:
            content = item.get("content", "").strip()
            if not content:
                continue

            # 去重
            if self.is_duplicate(content, existing):
                continue

            self._divergence_counter += 1
            entry = {
                "id": f"divergence_{self._divergence_counter}",
                "type": "divergence",
                "content": content,
                "opposing_pairs": item.get("opposing_pairs", []),
                "side_a": item.get("side_a", ""),
                "side_b": item.get("side_b", ""),
            }
            existing.append(entry)
            new_items.append(entry)

        return new_items
