# AI Panel Studio — 设计规格文档

**日期：** 2026-08-11
**版本：** v0.1.0
**状态：** 已确认

---

## 一、产品概述

**AI Panel Studio** 是一款 AI 驱动的圆桌讨论 Web 应用。用户输入话题后，系统调用 Deepseek API 自动生成主持人 + 多位专家嘉宾阵容，全自动推进多轮结构化讨论，最终输出共识与分歧总结。前端通过 SSE 实时流式接收发言内容。

---

## 二、技术选型

| 层次 | 技术 |
|------|------|
| 后端框架 | FastAPI (Python 3.11+) |
| 数据库 | SQLite + SQLAlchemy ORM |
| 异步 | asyncio + sse-starlette |
| LLM | Deepseek V4 Pro (`DEEPSEEK_API_KEY` 环境变量) |
| 前端 | 前后端分离（不在本阶段范围） |

---

## 三、项目结构

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI 入口，CORS、路由注册
│   ├── config.py            # 配置管理（环境变量读取）
│   ├── database.py          # SQLAlchemy 引擎 + SessionLocal
│   ├── models.py            # 5 个 ORM 模型
│   ├── schemas.py           # Pydantic 请求/响应 Schema
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── discussions.py   # 讨论 CRUD + 确认/结束
│   │   ├── guests.py        # 嘉宾生成
│   │   └── events.py        # SSE 流 + 共识/分歧查询
│   └── services/
│       ├── __init__.py
│       ├── discussion_service.py  # 讨论业务逻辑
│       ├── guest_service.py       # 嘉宾生成（调用 Deepseek）
│       ├── orchestration_service.py # 讨论编排引擎（核心）
│       └── llm_client.py          # Deepseek API 封装
├── requirements.txt
└── .env.example

docs/
├── PRD.md
├── ER.md
└── API.md
```

---

## 四、核心业务实体

### ER 关系

```
Discussion (1) ──< Guest (N)
Discussion (1) ──< Speech (N)
Discussion (1) ──< Consensus (N)
Discussion (1) ──< Divergence (N)
Guest (1) ──< Speech (N)
```

### Discussion（讨论）

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| `id` | UUID String | PK | 讨论唯一标识 |
| `topic` | String(200) | NOT NULL | 讨论话题 |
| `status` | String(20) | NOT NULL, default='pending' | pending → active → ended |
| `expert_count` | Integer | NOT NULL, default=3 | 专家人数（不含主持人） |
| `host_id` | UUID String | FK → guests.id, nullable | 确认嘉宾后回填 |
| `max_rounds` | Integer | NOT NULL, default=3 | 最大讨论轮次 |
| `current_round` | Integer | NOT NULL, default=0 | 当前轮次 |
| `created_at` | DateTime | NOT NULL, UTC | 创建时间 |
| `updated_at` | DateTime | NOT NULL, UTC, onupdate | 更新时间 |

### Guest（嘉宾）

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| `id` | UUID String | PK | 嘉宾唯一标识 |
| `discussion_id` | UUID String | FK → discussions.id, CASCADE | 所属讨论 |
| `name` | String(100) | NOT NULL | 嘉宾姓名 |
| `profession` | String(100) | NOT NULL | 职业 |
| `title` | String(200) | NOT NULL | 头衔/称号 |
| `stance` | Text | NOT NULL | 立场描述 |
| `color` | String(7) | NOT NULL | HEX 颜色码 |
| `role` | String(10) | NOT NULL, default='guest' | host / guest |
| `agent_state` | String(20) | NOT NULL, default='idle' | idle / ready / speaking / thinking |
| `created_at` | DateTime | NOT NULL, UTC | 创建时间 |

### Speech（发言）

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| `id` | UUID String | PK | 发言唯一标识 |
| `discussion_id` | UUID String | FK → discussions.id, CASCADE | 所属讨论 |
| `guest_id` | UUID String | FK → guests.id, SET NULL | 发言人 |
| `round_number` | Integer | NOT NULL | 所属轮次 |
| `content` | Text | NOT NULL | 发言内容 |
| `speech_type` | String(20) | NOT NULL | statement / question / reply / summary |
| `timestamp` | DateTime | NOT NULL, UTC | 发言时间 |

### Consensus（共识）

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| `id` | UUID String | PK | 共识唯一标识 |
| `discussion_id` | UUID String | FK → discussions.id, CASCADE | 所属讨论 |
| `content` | Text | NOT NULL | 共识内容 |
| `supporter_guest_ids` | JSON/Text | NOT NULL | 支持的嘉宾 ID 列表 |
| `created_at` | DateTime | NOT NULL, UTC | 创建时间 |
| `updated_at` | DateTime | NOT NULL, UTC | 更新时间 |

### Divergence（分歧）

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| `id` | UUID String | PK | 分歧唯一标识 |
| `discussion_id` | UUID String | FK → discussions.id, CASCADE | 所属讨论 |
| `content` | Text | NOT NULL | 分歧描述 |
| `opposing_pairs` | JSON/Text | NOT NULL | `[[guestId_A, guestId_B], ...]` |
| `created_at` | DateTime | NOT NULL, UTC | 创建时间 |
| `updated_at` | DateTime | NOT NULL, UTC | 更新时间 |

---

## 五、API 契约

### 讨论管理

| 方法 | 路径 | 说明 | 请求体 | 响应 |
|------|------|------|--------|------|
| `GET` | `/api/discussions` | 讨论列表 | — | `{ discussions: Discussion[], total: int }` |
| `POST` | `/api/discussions` | 发起新讨论 | `{ topic: str, expert_count: int, max_rounds?: int }` | `Discussion` |
| `GET` | `/api/discussions/{id}` | 讨论详情 | — | `Discussion + guests[] + speeches[]` |
| `POST` | `/api/discussions/{id}/confirm` | 确认嘉宾，开始讨论 | — | `{ status: "active" }` |
| `POST` | `/api/discussions/{id}/end` | 结束讨论 | — | `{ status: "ended" }` |

### 嘉宾生成

| 方法 | 路径 | 说明 | 响应 |
|------|------|------|------|
| `POST` | `/api/discussions/{id}/generate-guests` | LLM 生成 1 位主持人 + N 位专家（N = expert_count） | `Guest[]`（长度 = expert_count + 1） |

### 实时事件流

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/api/discussions/{id}/stream` | SSE 推送，事件类型见下方 |

**SSE 事件：**

| 事件名 | 数据 |
|--------|------|
| `speech_added` | `{ speech, round_number }` |
| `guest_state_changed` | `{ guest_id, agent_state }` |
| `consensus_updated` | `{ consensus }` |
| `divergence_updated` | `{ divergence }` |
| `discussion_ended` | `{ discussion_id, final_consensus[], final_divergence[] }` |
| `error` | `{ code, message }` |

### 共识与分歧

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/api/discussions/{id}/consensus` | 当前共识列表 |
| `GET` | `/api/discussions/{id}/divergence` | 当前分歧列表 |

---

## 六、讨论编排流程

```
POST /discussions → POST /generate-guests → POST /confirm
  → SSE stream 自动推进:
      Round 1: host开场 → guest1发言 → guest2发言 → ... → host小结
      Round 2: host追问 → guest1回应 → guest2回应 → ... → host小结
      ...
      Round N: 最终总结 → 生成共识/分歧 → discussion_ended
```

**编排策略：** 逐轮串行调用 Deepseek API，每轮中主持人和嘉宾依次发言，每位发言者携带完整讨论上下文。

**嘉宾生成策略：** 话题驱动智能匹配。用户提供话题（topic）+ 专家人数（expert_count），LLM 根据话题自动生成 **1 位主持人** + **N 位领域专家**，每位嘉宾包含 name、profession、title、stance、专属颜色（HEX）。主持人立场中立，各专家从不同角度/立场切入话题。

---

## 七、认证方案

**MVP 阶段不做认证。** 所有讨论公开可见，不设用户系统。

---

## 八、错误处理

| 状态码 | 场景 |
|--------|------|
| `400` | 参数校验失败、状态不允许操作（如重复确认） |
| `404` | 讨论/嘉宾不存在 |
| `500` | LLM API 调用失败、数据库异常 |
| `503` | Deepseek API 不可用或超时 |

---

## 九、高频查询索引

| 表 | 索引字段 |
|----|----------|
| discussions | `status`, `created_at` |
| guests | `discussion_id`, `role` |
| speeches | `discussion_id`, `guest_id`, `(discussion_id, round_number)` |
| consensus | `discussion_id` |
| divergence | `discussion_id` |

---

## 十、关键约束

- 数据库固定使用 SQLite + SQLAlchemy
- 前后端分离，后端框架使用 FastAPI
- 大模型 API Key 命名为 `DEEPSEEK_API_KEY`，仅从环境变量读取，不得硬编码
- 所有输出为中文
- 主键统一使用 UUID 字符串
- 所有时间字段使用 UTC 时区
- 外键明确级联策略（CASCADE / SET NULL）
