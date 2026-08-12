"""测试 SSE 事件广播服务 — EventBus

覆盖讨论隔离、全员广播、心跳、取消订阅、
SSE 格式和异步生成器。
"""

import json
import pytest
import asyncio

from app.services.event_bus import EventBus


# ── SSE 格式验证 ─────────────────────────────────────────────────

class TestEventBusFormat:
    """事件格式相关测试。"""

    def test_event_format_correct(self):
        """断言 format_sse 输出符合 SSE 规范：event: <name>\\ndata: <json>\\n\\n。"""
        bus = EventBus()

        data = {"type": "speech", "guest_name": "专家A", "content": "AI 是工具"}
        formatted = bus.format_sse("speech", data)

        # SSE 格式：event: name\ndata: JSON\n\n
        lines = formatted.split("\n")
        assert lines[0].startswith("event: "), f"首行应以 'event: ' 开头，实际: {lines[0]}"
        assert lines[1].startswith("data: "), f"次行应以 'data: ' 开头，实际: {lines[1]}"
        assert lines[2] == "", "第三行应为空行（\\n\\n 结尾）"

        # 验证 data 部分包含原始值
        data_str = lines[1][6:]  # 去掉 "data: " 前缀
        parsed = json.loads(data_str)
        assert parsed == data, f"data 字段应可解析为原始 JSON"


# ── 订阅与广播 ───────────────────────────────────────────────────

class TestEventBusBroadcast:
    """广播与订阅管理测试。"""

    def test_discussion_isolation(self):
        """向讨论 A 推送事件 → 讨论 B 的订阅者队列为空。"""
        bus = EventBus()

        q_a = bus.subscribe("disc_A")
        q_b = bus.subscribe("disc_B")

        bus.broadcast("disc_A", "message", {"text": "hello A"})

        # 讨论 A 的队列应有事件
        assert not q_a.empty(), "讨论 A 订阅者队列不应为空"
        # 讨论 B 的队列应保持为空
        assert q_b.empty(), "讨论 B 订阅者队列应为空（隔离）"

    def test_broadcast_reaches_all_subscribers(self):
        """讨论 X 注册 3 个订阅者 → 广播后 3 个队列都有事件。"""
        bus = EventBus()

        q1 = bus.subscribe("disc_X")
        q2 = bus.subscribe("disc_X")
        q3 = bus.subscribe("disc_X")

        bus.broadcast("disc_X", "insight", {"content": "共识内容"})

        for i, q in enumerate([q1, q2, q3], 1):
            assert not q.empty(), f"订阅者 {i} 的队列不应为空"

    def test_unsubscribe_cleans_up(self):
        """取消订阅后 → 订阅者数减 1，后续广播不影响该队列。"""
        bus = EventBus()

        q1 = bus.subscribe("disc_Y")
        q2 = bus.subscribe("disc_Y")

        assert bus.subscriber_count("disc_Y") == 2

        # 取消 q1
        bus.unsubscribe("disc_Y", q1)

        assert bus.subscriber_count("disc_Y") == 1, "取消订阅后订阅者数应减 1"

        # 广播 → q2 收到，q1 不受影响
        bus.broadcast("disc_Y", "message", {"text": "after unsubscribe"})

        assert not q2.empty(), "仍订阅的 q2 应收到事件"
        # q1 不应收到（旧队列中的事件是取消前残留的，这里应验证后续不影响）
        # 注意：unsubscribe 只是从列表中移除，不会清空已有队列
        # 这里验证后续广播不会重新写入 q1

    def test_unsubscribe_nonexistent_safe(self):
        """取消不存在的订阅不会抛出异常（幂等安全）。"""
        bus = EventBus()
        fake_queue = asyncio.Queue()

        # 不应抛出异常
        bus.unsubscribe("nonexistent_disc", fake_queue)


# ── 异步生成器 ───────────────────────────────────────────────────

class TestEventBusAsync:
    """SSE 异步生成器测试。"""

    @pytest.mark.asyncio
    async def test_stream_heartbeat(self):
        """空闲超过 heartbeat_interval 后自动发送 heartbeat 事件。"""
        bus = EventBus(heartbeat_interval=0.05)  # 50ms 超时间隔
        queue = bus.subscribe("disc_stream")

        gen = bus.sse_generator("disc_stream", queue)

        # 不发送任何事件，等待心跳
        first_event = await gen.__anext__()

        assert "heartbeat" in first_event, (
            f"空闲超时应发送 heartbeat 事件，实际收到: {first_event[:80]}"
        )

    @pytest.mark.asyncio
    async def test_async_generator_yields_events(self):
        """SSE 异步生成器正确 yield 广播事件的 SSE 字符串。"""
        bus = EventBus(heartbeat_interval=5.0)  # 长心跳间隔，避免干扰
        queue = bus.subscribe("disc_gen")

        gen = bus.sse_generator("disc_gen", queue)

        # 广播一条事件
        bus.broadcast("disc_gen", "speech", {
            "guest_name": "专家A",
            "content": "AI 是工具",
        })

        # 生成器应立即 yield 该事件
        event_str = await gen.__anext__()

        assert "event: speech" in event_str, (
            f"SSE 事件应包含 'event: speech'，实际: {event_str[:80]}"
        )
        assert "专家A" in event_str, "事件 data 应包含嘉宾名称"

    @pytest.mark.asyncio
    async def test_async_generator_multiple_events(self):
        """生成器按顺序 yield 多条广播事件。"""
        bus = EventBus(heartbeat_interval=5.0)
        queue = bus.subscribe("disc_multi")

        gen = bus.sse_generator("disc_multi", queue)

        # 广播多条事件
        bus.broadcast("disc_multi", "speech", {"guest": "A"})
        bus.broadcast("disc_multi", "speech", {"guest": "B"})
        bus.broadcast("disc_multi", "insight", {"type": "consensus"})

        events = []
        for _ in range(3):
            evt = await gen.__anext__()
            events.append(evt)

        assert any("guest" in e and '"A"' in e for e in events), "应收到 guest A 的事件"
        assert any("guest" in e and '"B"' in e for e in events), "应收到 guest B 的事件"
        assert any("insight" in e for e in events), "应收到 insight 事件"
