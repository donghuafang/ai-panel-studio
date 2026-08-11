# AI Panel Studio — 实体关系文档 (ER)

## 实体关系图

```mermaid
erDiagram
    Discussion ||--o{ Guest : has
    Discussion ||--o{ Speech : contains
    Discussion ||--o{ Consensus : produces
    Discussion ||--o{ Divergence : produces
    Guest ||--o{ Speech : makes

    Discussion {
        string id PK "UUID"
        string topic "讨论话题"
        string status "pending|active|ended"
        int expert_count "专家人数"
        string host_id FK "主持人ID, nullable"
        int max_rounds "最大轮次"
        int current_round "当前轮次"
        datetime created_at "UTC"
        datetime updated_at "UTC"
    }

    Guest {
        string id PK "UUID"
        string discussion_id FK "CASCADE"
        string name "嘉宾姓名"
        string profession "职业"
        string title "头衔/称号"
        text stance "立场描述"
        string color "HEX颜色码"
        string role "host|guest"
        string agent_state "idle|ready|speaking|thinking"
        datetime created_at "UTC"
    }

    Speech {
        string id PK "UUID"
        string discussion_id FK "CASCADE"
        string guest_id FK "SET NULL"
        int round_number "所属轮次"
        text content "发言内容"
        string speech_type "statement|question|reply|summary"
        datetime timestamp "UTC"
    }

    Consensus {
        string id PK "UUID"
        string discussion_id FK "CASCADE"
        text content "共识内容"
        json supporter_guest_ids "支持的嘉宾ID列表"
        datetime created_at "UTC"
        datetime updated_at "UTC"
    }

    Divergence {
        string id PK "UUID"
        string discussion_id FK "CASCADE"
        text content "分歧描述"
        json opposing_pairs "[[guestA, guestB], ...]"
        datetime created_at "UTC"
        datetime updated_at "UTC"
    }
```

## 关系说明

| 关系 | 类型 | 级联 |
|------|------|------|
| Discussion → Guest | 1:N | CASCADE 删除 |
| Discussion → Speech | 1:N | CASCADE 删除 |
| Discussion → Consensus | 1:N | CASCADE 删除 |
| Discussion → Divergence | 1:N | CASCADE 删除 |
| Guest → Speech | 1:N | SET NULL（嘉宾删除后发言保留但匿名） |

## 索引设计

| 表 | 索引 | 用途 |
|----|------|------|
| discussions | `status` | 按状态筛选 |
| discussions | `created_at` | 按时间排序 |
| guests | `discussion_id` | 查询讨论下的嘉宾 |
| guests | `role` | 区分主持人/专家 |
| speeches | `discussion_id` | 查询讨论下的发言 |
| speeches | `guest_id` | 查询嘉宾的发言 |
| speeches | `(discussion_id, round_number)` | 按轮次查询发言 |
| consensus | `discussion_id` | 查询讨论下的共识 |
| divergence | `discussion_id` | 查询讨论下的分歧 |
