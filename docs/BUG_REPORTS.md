# AI Panel Studio — Bug 报告

> **阶段**: Phase 4 E2E 端到端测试
> **日期**: 2026-08-11

---

## 已知问题（代码审查发现）

### BUG-001: GuestGenerator/SpeechScheduler 未集成到生产代码

**严重程度**: Medium

**复现步骤:**
1. 查看 `app/services/orchestration_service.py` — 直接调用 `LLMClient.generate_speech()`
2. 查看 `app/services/guest_service.py` — 直接调用 `LLMClient.generate_guests()`
3. 对比 `app/services/guest_generator.py` 和 `app/services/speech_scheduler.py` — 已实现但未被使用

**根因分析:**
Phase 3 TDD 阶段创建的 4 个服务模块（GuestGenerator, SpeechScheduler, InsightExtractor, EventBus）未集成到现有的生产代码路径中。orchestrator 和 guest_service 仍使用旧架构（直接调用 LLMClient）。

**修复方案:**
1. 在 `guest_service.py` 中注入 `GuestGenerator`，替换直接的 `llm.generate_guests()` 调用
2. 在 `orchestration_service.py` 中注入 `SpeechScheduler`，替换硬编码的轮流发言逻辑
3. 在 `orchestration_service.py` 中注入 `InsightExtractor`，替换内联的共识/分歧提炼逻辑
4. 确保所有服务通过依赖注入获取 LLMClient，保持可测试性

**状态**: ⬜ 待修复

---

### BUG-002: orchestration_service.py 使用 threading.Lock + asyncio.run() 可能导致死锁

**严重程度**: Low (MVP 阶段影响有限)

**复现步骤:**
1. `orchestration_service.py` 在 daemon thread 中使用 `threading.Lock` 管理订阅者
2. 同一线程中通过 `asyncio.run()` 调用异步 LLM 方法
3. `events.py` 路由的 `sse_generator` 是异步的，可能在事件循环中等待

**根因分析:**
混合使用线程和 asyncio 的同步原语。在 MVP 阶段，单用户低并发场景不会触发问题，但在高并发下可能出现竞态条件。

**修复方案:**
改为全异步架构：将后台编排改为 `asyncio.create_task()`，使用 `asyncio.Lock` 替代 `threading.Lock`。

**状态**: ⬜ 待修复（建议在 Phase 5 多用户支持时处理）

---

### BUG-003: 前端 SSE 重连逻辑可能丢失事件

**严重程度**: Medium

**复现步骤:**
1. 讨论进行中关闭浏览器标签页
2. 重新打开标签页进入同一讨论
3. SSE 重新连接，但中间的事件（发言、状态变更）永久丢失

**根因分析:**
当前 SSE 是纯推送流，没有事件序列号或断点续传机制。`useDiscussionStream` 的 `onConnectionChange` 回调触发重连后，前端通过 `GET /api/discussions/{id}` 获取当前快照，但已丢失的中间事件不会被补发。

**修复方案:**
1. 在后端添加事件序列号（每个 SSE 事件携带递增 seq）
2. 前端重连时发送 `Last-Event-ID` header
3. 后端根据 Last-Event-ID 补发遗漏事件

**状态**: ⬜ 待修复（建议在 Phase 5 可靠性改进时处理）

---

## E2E 测试中发现的 Bug

### BUG-E2E-001: 讨论自动结束后前端不显示"讨论已结束"横幅

**复现步骤:**
1. 创建讨论 → 生成嘉宾 → 确认进入演播厅
2. 后端 orchestrator 在后台线程快速完成所有轮次（Mock LLM 无延迟）
3. SSE `discussion_ended` 事件广播时前端可能尚未连接，或 SSE 事件到达后 `setEnded` 将 `discussion` 设为 null
4. 前端 `status = discussion?.status || detail?.status || 'ended'` 回退到 `detail.status`
5. `detail` 在讨论开始时获取，`status` 仍为 `'active'`
6. `isActive = true` → 条件 `showEnded && !isActive` 为 false → 横幅不显示

**根因分析:**
`useDiscussionStore.setEnded()` 将 `discussion` 设为 `null`，导致 status 计算回退到过时的 `detail.status`（'active'），使 `isActive` 保持 `true`，阻止了结束横幅的渲染。

**修复方案:**
修改 `setEnded` 不将 `discussion` 设为 null，而是将其 `status` 更新为 `'ended'`：
```typescript
set((state) => ({
  isEnded: true,
  discussion: state.discussion
    ? { ...state.discussion, status: 'ended' as const }
    : null,
}))
```

**状态:** ✅ 已修复

---

### BUG-E2E-002: SSE 订阅竞态条件 — orchestrator 可能在订阅前完成

**复现步骤:**
1. POST /confirm 立即启动后台 orchestrator 线程
2. 前端导航到 /studio/{id} 后建立 SSE 连接
3. 若 orchestrator 在 SSE connect 前完成所有轮次，`discussion_ended` 事件广播时无订阅者
4. 前端错过结束事件

**根因分析:**
`orchestration_service.py` 的 `run_discussion` 在 daemon thread 中立即开始生成发言，无任何等待。Mock LLM 模式下发言几乎瞬时生成，导致 orchestrator 可能在 SSE 连接建立前完成。

**修复方案:**
在 `run_discussion` 开始时添加 1 秒延迟：
```python
time.sleep(1.0)  # 给前端 SSE 连接留出时间
```

**状态:** ✅ 已修复

---

### BUG-E2E-003: LLMClient Mock 模式在无 API Key 时未自动启用

**复现步骤:**
1. 未设置 `MOCK_LLM=true` 环境变量
2. 后端启动，`LLMClient.__init__` 检查 `os.environ.get("MOCK_LLM")`
3. 未配置 DeepSeek API Key（`DEEPSEEK_API_KEY=""`）
4. 请求 `/api/discussions/{id}/generate-guests` 报错 "Illegal header value b'Bearer '"

**根因分析:**
`LLMClient.mock_mode` 仅检查环境变量 `MOCK_LLM`，未考虑 API Key 为空的情况。当 API Key 为空时，`_headers` 属性生成非法 HTTP header。

**修复方案:**
```python
self.mock_mode = (
    os.environ.get("MOCK_LLM", "").lower() == "true"
    or not self.api_key  # 没有 API key 时自动进入 mock 模式
)
```

**状态:** ✅ 已修复

---

## 已修复的 Bug

| ID | 描述 | 修复 Commit | 日期 |
|----|------|-------------|------|
| BUG-E2E-001 | 讨论结束后不显示横幅（setEnded 设 discussion=null） | — | 2026-08-11 |
| BUG-E2E-002 | SSE 订阅竞态条件（orchestrator 提前完成） | — | 2026-08-11 |
| BUG-E2E-003 | 无 API Key 时未自动启用 Mock 模式 | — | 2026-08-11 |
