"""SSE 事件广播服务 — EventBus

负责：
1. 按讨论隔离的异步事件队列管理
2. 订阅/取消订阅机制
3. SSE 格式事件序列化
4. 异步生成器（SSE 流 + 心跳保活）
"""

import asyncio
import json
from datetime import datetime, timezone


class EventBus:
    """按讨论隔离的 SSE 事件总线。

    每个讨论维护独立的 asyncio.Queue 列表，广播事件时推送到
    该讨论的所有订阅者队列。支持 SSE 格式化和心跳保活。

    用法:
        bus = EventBus(heartbeat_interval=15.0)
        q = bus.subscribe("disc_123")
        bus.broadcast("disc_123", "speech", {"content": "..."})

        async for sse_str in bus.sse_generator("disc_123", q):
            yield sse_str  # 通过 SSE 发送给前端
    """

    def __init__(self, heartbeat_interval: float = 15.0):
        """初始化事件总线。

        Args:
            heartbeat_interval: 心跳间隔（秒），超时后自动发送 heartbeat 事件。
                               测试中可设为较小值（如 0.05）。
        """
        self._queues: dict[str, list[asyncio.Queue]] = {}
        self._heartbeat_interval = heartbeat_interval

    # ── SSE 格式序列化 ────────────────────────────────────────

    def format_sse(self, event: str, data: dict) -> str:
        """将事件序列化为 SSE 文本格式。

        输出格式:
            event: <name>
            data: <json>
            <空行>

        Args:
            event: 事件类型名（如 "speech", "heartbeat", "insight"）
            data: 事件数据字典

        Returns:
            str: SSE 格式字符串
        """
        json_str = json.dumps(data, ensure_ascii=False)
        return f"event: {event}\ndata: {json_str}\n\n"

    # ── 订阅管理 ──────────────────────────────────────────────

    def subscribe(self, discussion_id: str) -> asyncio.Queue:
        """为指定讨论创建一个新的订阅队列。

        Args:
            discussion_id: 讨论 ID

        Returns:
            asyncio.Queue: 该订阅者的事件队列
        """
        queue: asyncio.Queue = asyncio.Queue()
        if discussion_id not in self._queues:
            self._queues[discussion_id] = []
        self._queues[discussion_id].append(queue)
        return queue

    def unsubscribe(self, discussion_id: str, queue: asyncio.Queue) -> None:
        """取消订阅，从讨论的订阅者列表中移除指定队列。

        如果移除后该讨论无订阅者，清理讨论条目。
        取消不存在的队列为安全空操作。

        Args:
            discussion_id: 讨论 ID
            queue: 之前 subscribe 返回的队列
        """
        if discussion_id not in self._queues:
            return
        try:
            self._queues[discussion_id].remove(queue)
        except ValueError:
            pass  # 队列不存在于列表中，安全忽略
        if not self._queues[discussion_id]:
            del self._queues[discussion_id]

    def subscriber_count(self, discussion_id: str) -> int:
        """返回指定讨论的当前订阅者数量。

        Args:
            discussion_id: 讨论 ID

        Returns:
            int: 订阅者数量
        """
        return len(self._queues.get(discussion_id, []))

    # ── 事件广播 ──────────────────────────────────────────────

    def broadcast(self, discussion_id: str, event: str, data: dict) -> None:
        """向指定讨论的所有订阅者广播事件。

        使用 put_nowait 非阻塞写入，确保不会阻塞调用方。

        Args:
            discussion_id: 目标讨论 ID
            event: 事件类型名
            data: 事件数据字典
        """
        if discussion_id not in self._queues:
            return
        formatted = self.format_sse(event, data)
        for q in self._queues[discussion_id]:
            q.put_nowait(formatted)

    # ── SSE 异步生成器 ────────────────────────────────────────

    async def sse_generator(
        self, discussion_id: str, queue: asyncio.Queue
    ):
        """SSE 事件异步生成器，持续产出 SSE 格式字符串。

        空闲超过 heartbeat_interval 时自动发送心跳事件，
        防止 SSE 连接被代理/浏览器超时断开。

        Args:
            discussion_id: 讨论 ID（用于心跳事件的标识）
            queue: 该订阅者的 asyncio.Queue

        Yields:
            str: SSE 格式的事件字符串（包括心跳）
        """
        while True:
            try:
                event_str = await asyncio.wait_for(
                    queue.get(),
                    timeout=self._heartbeat_interval,
                )
                yield event_str
            except asyncio.TimeoutError:
                # 空闲超时 → 发送心跳
                heartbeat = self.format_sse("heartbeat", {
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "discussion_id": discussion_id,
                })
                yield heartbeat
