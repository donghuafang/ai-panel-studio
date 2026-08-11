# AI Panel Studio — API 契约文档

## 基础信息

- **Base URL:** `http://localhost:8000`
- **Content-Type:** `application/json`
- **认证:** MVP 阶段无需认证

---

## 1. 讨论管理

### 1.1 获取讨论列表

| 项目 | 内容 |
|------|------|
| **方法** | `GET` |
| **路径** | `/api/discussions` |
| **查询参数** | `page` (int, default=1), `page_size` (int, default=20) |
| **成功响应** | `200` |

**响应体：**
```json
{
  "discussions": [
    {
      "id": "uuid-string",
      "topic": "AI 会取代程序员吗",
      "status": "pending",
      "expert_count": 3,
      "host_id": null,
      "max_rounds": 3,
      "current_round": 0,
      "created_at": "2026-08-11T10:00:00Z",
      "updated_at": "2026-08-11T10:00:00Z"
    }
  ],
  "total": 1
}
```

### 1.2 发起新讨论

| 项目 | 内容 |
|------|------|
| **方法** | `POST` |
| **路径** | `/api/discussions` |
| **请求体** | 见下方 |
| **成功响应** | `201` |
| **错误** | `400` 参数校验失败 |

**请求体：**
```json
{
  "topic": "AI 会取代程序员吗",
  "expert_count": 3,
  "max_rounds": 3
}
```

**响应体：** `Discussion` 对象（同 1.1 中的单项结构）

### 1.3 获取讨论详情

| 项目 | 内容 |
|------|------|
| **方法** | `GET` |
| **路径** | `/api/discussions/{id}` |
| **成功响应** | `200` |
| **错误** | `404` 讨论不存在 |

**响应体：** `Discussion` + `guests[]` + `speeches[]`

```json
{
  "id": "uuid",
  "topic": "...",
  "status": "active",
  "expert_count": 3,
  "host_id": "uuid",
  "max_rounds": 3,
  "current_round": 1,
  "created_at": "...",
  "updated_at": "...",
  "guests": [ { "id": "...", "name": "...", ... } ],
  "speeches": [ { "id": "...", "content": "...", ... } ]
}
```

### 1.4 确认嘉宾并开始讨论

| 项目 | 内容 |
|------|------|
| **方法** | `POST` |
| **路径** | `/api/discussions/{id}/confirm` |
| **成功响应** | `200` |
| **错误** | `400` 状态不允许（非 pending 状态）`404` 不存在 |

**响应体：**
```json
{ "status": "active" }
```

> 调用后，后端启动后台编排引擎，SSE 流开始推送事件。

### 1.5 结束讨论

| 项目 | 内容 |
|------|------|
| **方法** | `POST` |
| **路径** | `/api/discussions/{id}/end` |
| **成功响应** | `200` |
| **错误** | `400` 状态不允许 `404` 不存在 |

**响应体：**
```json
{ "status": "ended" }
```

---

## 2. 嘉宾生成

### 2.1 生成嘉宾阵容

| 项目 | 内容 |
|------|------|
| **方法** | `POST` |
| **路径** | `/api/discussions/{id}/generate-guests` |
| **说明** | 调用 Deepseek API 生成 1 位主持人 + N 位专家（N = expert_count） |
| **成功响应** | `200` |
| **错误** | `400` 状态不允许 `503` LLM 服务不可用 |

**响应体：**
```json
{
  "guests": [
    {
      "id": "uuid",
      "discussion_id": "uuid",
      "name": "张明",
      "profession": "科技媒体主编",
      "title": "资深科技评论员",
      "stance": "作为中立主持人，致力于引导各方充分表达观点...",
      "color": "#4A90D9",
      "role": "host",
      "agent_state": "ready",
      "created_at": "2026-08-11T10:00:00Z"
    },
    {
      "id": "uuid",
      "discussion_id": "uuid",
      "name": "李伟",
      "profession": "软件工程师",
      "title": "资深全栈开发者",
      "stance": "认为 AI 将大幅提升编程效率，但创造力仍然是人类的核心优势...",
      "color": "#FF6B6B",
      "role": "guest",
      "agent_state": "ready",
      "created_at": "2026-08-11T10:00:00Z"
    }
  ]
}
```

---

## 3. 实时事件流 (SSE)

### 3.1 订阅讨论事件

| 项目 | 内容 |
|------|------|
| **方法** | `GET` |
| **路径** | `/api/discussions/{id}/stream` |
| **Content-Type** | `text/event-stream` |

**事件类型：**

#### `speech_added`
```
event: speech_added
data: {"speech": {...}, "round_number": 1}
```

#### `guest_state_changed`
```
event: guest_state_changed
data: {"guest_id": "uuid", "agent_state": "speaking"}
```

#### `consensus_updated`
```
event: consensus_updated
data: {"consensus": {...}}
```

#### `divergence_updated`
```
event: divergence_updated
data: {"divergence": {...}}
```

#### `discussion_ended`
```
event: discussion_ended
data: {"discussion_id": "uuid", "final_consensus": [...], "final_divergence": [...]}
```

#### `error`
```
event: error
data: {"code": "ORCHESTRATION_ERROR", "message": "..."}
```

#### `ping`（心跳，每 15 秒）
```
event: ping
data: {}
```

---

## 4. 共识与分歧

### 4.1 获取共识列表

| 项目 | 内容 |
|------|------|
| **方法** | `GET` |
| **路径** | `/api/discussions/{id}/consensus` |

**响应体：**
```json
[
  {
    "id": "uuid",
    "discussion_id": "uuid",
    "content": "AI 工具确实在改变编程工作方式，但...",
    "supporter_guest_ids": ["uuid1", "uuid2"],
    "created_at": "...",
    "updated_at": "..."
  }
]
```

### 4.2 获取分歧列表

| 项目 | 内容 |
|------|------|
| **方法** | `GET` |
| **路径** | `/api/discussions/{id}/divergence` |

**响应体：**
```json
[
  {
    "id": "uuid",
    "discussion_id": "uuid",
    "content": "关于 AI 是否会在 5 年内取代初级程序员存在分歧",
    "opposing_pairs": [["uuid1", "uuid2"]],
    "created_at": "...",
    "updated_at": "..."
  }
]
```

---

## 5. 健康检查

| 方法 | 路径 | 响应 |
|------|------|------|
| `GET` | `/api/health` | `{"status": "ok"}` |

---

## 错误码汇总

| 状态码 | 含义 | 触发场景 |
|--------|------|----------|
| `200` | 成功 | 正常响应 |
| `201` | 已创建 | POST 创建资源成功 |
| `400` | 请求错误 | 参数校验失败、状态不允许操作 |
| `404` | 未找到 | 讨论/资源不存在 |
| `500` | 服务器错误 | 数据库异常、未捕获异常 |
| `503` | 服务不可用 | Deepseek API 调用失败或超时 |
