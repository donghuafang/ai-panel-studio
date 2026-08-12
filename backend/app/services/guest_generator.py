"""嘉宾生成服务 — GuestGenerator

负责：
1. 调用 LLM 生成 1 位主持人 + N 位专家嘉宾
2. 预定义颜色池循环分配，确保颜色互不相同
3. 校验 guest_count 范围、API Key 存在性
4. 自动重试 2 次（指数退避 1s → 2s）
"""

import os
import asyncio

COLOR_POOL = [
    "#FF6B6B",  # 珊瑚红
    "#4ECDC4",  # 青绿
    "#45B7D1",  # 天蓝
    "#96CEB4",  # 薄荷绿
    "#FFEAA7",  # 鹅黄
    "#DDA0DD",  # 淡紫
    "#F7DC6F",  # 金菊黄
    "#FF8A5C",  # 橙红
]


class GuestGenerator:
    """嘉宾生成器：封装 LLM 调用、颜色分配、输入校验与重试逻辑。

    用法:
        generator = GuestGenerator(llm_client)
        guests = await generator.generate("AI 话题", expert_count=4)
    """

    def __init__(self, llm_client):
        """注入 LLM 客户端（便于测试 Mock）。

        Args:
            llm_client: 实现了 generate_guests(topic, expert_count) -> list[dict] 的对象
        """
        self.llm = llm_client
        self.max_retries = 2

    # ── 输入校验 ─────────────────────────────────────────────

    def validate_count(self, count: int) -> None:
        """校验专家人数在有效范围内（2-8）。"""
        if count < 2 or count > 8:
            raise ValueError(f"专家人数必须在 2-8 之间，当前为 {count}")

    def validate_api_key(self) -> None:
        """校验 DEEPSEEK_API_KEY 环境变量已配置。"""
        if not os.environ.get("DEEPSEEK_API_KEY"):
            raise RuntimeError("DEEPSEEK_API_KEY 未配置，请在环境变量或 .env 文件中设置")

    # ── 颜色分配 ─────────────────────────────────────────────

    def _assign_colors(self, guests: list[dict]) -> list[dict]:
        """为缺少颜色的嘉宾从预定义色池中分配，确保各嘉宾颜色互不相同。

        已有 valid 颜色的嘉宾保持不变；空字符串或缺失的会被覆盖。
        """
        # 收集已使用的颜色
        used_colors = {
            g["color"] for g in guests if g.get("color") and g["color"].startswith("#")
        }
        # 从色池中取未使用的颜色
        available = [c for c in COLOR_POOL if c not in used_colors]

        color_idx = 0
        for g in guests:
            if not g.get("color") or not g["color"].startswith("#"):
                if color_idx < len(available):
                    g["color"] = available[color_idx]
                    color_idx += 1
                else:
                    # 色池耗尽时循环复用（极端情况兜底）
                    g["color"] = COLOR_POOL[color_idx % len(COLOR_POOL)]
                    color_idx += 1
        return guests

    # ── 核心生成逻辑 ─────────────────────────────────────────

    async def generate(self, topic: str, expert_count: int) -> list[dict]:
        """生成嘉宾阵容：1 host + expert_count guests。

        Args:
            topic: 讨论话题
            expert_count: 专家人数（2-8）

        Returns:
            list[dict]: 嘉宾列表，第一位为主持人，其余为专家。
                       每个 dict 包含 name, profession, title, stance, color, role。

        Raises:
            ValueError: expert_count 不在 2-8 范围内
            RuntimeError: DEEPSEEK_API_KEY 未配置
        """
        self.validate_count(expert_count)
        self.validate_api_key()

        for attempt in range(self.max_retries + 1):
            try:
                # 调用 LLM 生成嘉宾数据
                guests = await self.llm.generate_guests(topic, expert_count)

                # 校验第一条为主持人
                if not guests or guests[0].get("role") != "host":
                    raise ValueError("LLM 返回的嘉宾列表第一条必须为 role='host'")

                # 校验总人数 = 1 host + expert_count guests
                expected = expert_count + 1
                if len(guests) != expected:
                    raise ValueError(
                        f"LLM 返回嘉宾数量不符：期望 {expected} 人，实际 {len(guests)} 人"
                    )

                # 分配颜色
                self._assign_colors(guests)

                return guests

            except Exception:
                if attempt == self.max_retries:
                    raise
                await asyncio.sleep(2 ** attempt)  # 1s, 2s

        # 不可达（raise 在循环中），但保持类型安全
        raise RuntimeError("嘉宾生成失败，已达最大重试次数")
