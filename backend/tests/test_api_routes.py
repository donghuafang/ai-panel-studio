"""AI Panel Studio — API 路由集成测试

使用 FastAPI TestClient + 内存数据库覆盖所有 REST 端点。
所有 LLM 调用被 Mock，测试可在 CI 环境离线运行。
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient

from app.main import app
from app.database import Base, SessionLocal
from app.models import Discussion, Guest, Speech
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool


# ── 内存数据库 Fixtures ──────────────────────────────────────────

@pytest.fixture(scope="function")
def db_session():
    """为每个测试创建独立的内存 SQLite 数据库"""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    from sqlalchemy import event
    @event.listens_for(engine, "connect")
    def _set_pragma(dbapi_connection, _record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys = ON")
        cursor.close()

    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


@pytest.fixture(scope="function")
def client(db_session):
    """创建 TestClient，并注入内存数据库 session"""
    def _override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides.clear()
    from app.database import get_db
    app.dependency_overrides[get_db] = _override_get_db

    with TestClient(app) as c:
        yield c

    app.dependency_overrides.clear()


# ── 辅助函数 ──────────────────────────────────────────────────────

def create_discussion(client, topic="测试话题", expert_count=3, max_rounds=3):
    """创建讨论并返回 JSON"""
    resp = client.post("/api/discussions", json={
        "topic": topic,
        "expert_count": expert_count,
        "max_rounds": max_rounds,
    })
    return resp


def create_discussion_with_guests(client, db_session, topic="测试话题"):
    """创建讨论 + 手动添加嘉宾，返回 discussion JSON"""
    resp = create_discussion(client, topic)
    assert resp.status_code == 201
    disc = resp.json()

    host = Guest(
        discussion_id=disc["id"],
        name="测试主持人",
        profession="测试",
        title="测试",
        stance="中立",
        color="#4A90D9",
        role="host",
        agent_state="ready",
    )
    expert = Guest(
        discussion_id=disc["id"],
        name="测试专家",
        profession="测试",
        title="测试",
        stance="支持 AI",
        color="#FF6B6B",
        role="guest",
        agent_state="ready",
    )
    db_session.add_all([host, expert])
    db_session.commit()
    db_session.refresh(host)
    # 回填 host_id
    disc_obj = db_session.query(Discussion).filter(Discussion.id == disc["id"]).first()
    disc_obj.host_id = host.id
    db_session.commit()

    return disc


# ══════════════════════════════════════════════════════════════════
# 1. 健康检查
# ══════════════════════════════════════════════════════════════════

class TestHealthCheck:
    def test_health_returns_ok(self, client):
        resp = client.get("/api/health")
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}


# ══════════════════════════════════════════════════════════════════
# 2. 讨论 CRUD
# ══════════════════════════════════════════════════════════════════

class TestCreateDiscussion:
    def test_create_discussion_success(self, client):
        resp = create_discussion(client, "AI 会取代程序员吗", 3, 3)
        assert resp.status_code == 201
        data = resp.json()
        assert data["topic"] == "AI 会取代程序员吗"
        assert data["status"] == "pending"
        assert data["expert_count"] == 3
        assert data["max_rounds"] == 3
        assert data["current_round"] == 0
        assert "id" in data
        assert "created_at" in data

    def test_create_discussion_default_values(self, client):
        resp = client.post("/api/discussions", json={"topic": "测试"})
        assert resp.status_code == 201
        data = resp.json()
        assert data["expert_count"] == 3
        assert data["max_rounds"] == 3

    def test_create_discussion_empty_topic(self, client):
        resp = client.post("/api/discussions", json={"topic": ""})
        assert resp.status_code == 422

    def test_create_discussion_topic_too_long(self, client):
        resp = client.post("/api/discussions", json={"topic": "A" * 201})
        assert resp.status_code == 422

    def test_create_discussion_invalid_expert_count(self, client):
        resp = client.post("/api/discussions", json={
            "topic": "测试", "expert_count": 0,
        })
        assert resp.status_code == 422

    def test_create_discussion_expert_count_too_high(self, client):
        resp = client.post("/api/discussions", json={
            "topic": "测试", "expert_count": 11,
        })
        assert resp.status_code == 422

    def test_create_discussion_invalid_max_rounds(self, client):
        resp = client.post("/api/discussions", json={
            "topic": "测试", "max_rounds": 0,
        })
        assert resp.status_code == 422


class TestListDiscussions:
    def test_list_empty(self, client):
        resp = client.get("/api/discussions")
        assert resp.status_code == 200
        data = resp.json()
        assert data["discussions"] == []
        assert data["total"] == 0

    def test_list_with_discussions(self, client):
        create_discussion(client, "话题 A")
        create_discussion(client, "话题 B")
        create_discussion(client, "话题 C")

        resp = client.get("/api/discussions")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 3
        assert len(data["discussions"]) == 3

    def test_list_pagination(self, client):
        for i in range(5):
            create_discussion(client, f"话题 {i}")

        resp = client.get("/api/discussions?page=1&page_size=2")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["discussions"]) == 2
        assert data["total"] == 5

    def test_list_default_page_size(self, client):
        for i in range(25):
            create_discussion(client, f"话题 {i}")

        resp = client.get("/api/discussions")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["discussions"]) <= 20


class TestGetDiscussion:
    def test_get_existing_discussion(self, client, db_session):
        resp = create_discussion(client, "测试话题")
        disc_id = resp.json()["id"]

        resp = client.get(f"/api/discussions/{disc_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["topic"] == "测试话题"
        assert "guests" in data
        assert "speeches" in data

    def test_get_nonexistent_discussion(self, client):
        resp = client.get("/api/discussions/nonexistent-id")
        assert resp.status_code == 404

    def test_get_discussion_includes_guests(self, client, db_session):
        disc = create_discussion_with_guests(client, db_session, "带嘉宾的讨论")

        resp = client.get(f"/api/discussions/{disc['id']}")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["guests"]) == 2


# ══════════════════════════════════════════════════════════════════
# 3. 嘉宾生成
# ══════════════════════════════════════════════════════════════════

class TestGenerateGuests:
    def test_generate_guests_with_mock(self, client):
        """Mock 模式下生成嘉宾（无 API Key 时自动 fallback）"""
        resp = create_discussion(client, "AI 伦理", expert_count=3)
        disc_id = resp.json()["id"]

        resp = client.post(f"/api/discussions/{disc_id}/generate-guests")
        assert resp.status_code == 200
        data = resp.json()
        assert "guests" in data
        guests = data["guests"]
        assert len(guests) == 4  # 1 host + 3 experts
        # 第一个应该是主持人
        assert guests[0]["role"] == "host"
        # 其余是专家
        for g in guests[1:]:
            assert g["role"] == "guest"
        # 验证必填字段
        for g in guests:
            assert g["name"]
            assert g["profession"]
            assert g["stance"]
            assert g["color"].startswith("#")

    def test_generate_guests_nonexistent_discussion(self, client):
        resp = client.post("/api/discussions/nonexistent/generate-guests")
        assert resp.status_code == 400  # ValueError → 400

    def test_generate_guests_wrong_status(self, client, db_session):
        """已 active 的讨论不能重新生成嘉宾"""
        disc = create_discussion_with_guests(client, db_session, "已开始的讨论")
        # 手动设为 active
        disc_obj = db_session.query(Discussion).filter(Discussion.id == disc["id"]).first()
        disc_obj.status = "active"
        db_session.commit()

        resp = client.post(f"/api/discussions/{disc['id']}/generate-guests")
        assert resp.status_code == 400


# ══════════════════════════════════════════════════════════════════
# 4. 确认与结束讨论
# ══════════════════════════════════════════════════════════════════

class TestConfirmDiscussion:
    @pytest.mark.skip(reason="confirm spawns background thread; tested in E2E")
    def test_confirm_pending_discussion(self, client, db_session):
        disc = create_discussion_with_guests(client, db_session, "待确认的讨论")
        resp = client.post(f"/api/discussions/{disc['id']}/confirm")
        assert resp.status_code == 200
        assert resp.json()["status"] == "active"

    @pytest.mark.skip(reason="confirm spawns background thread; tested in E2E")
    def test_confirm_already_active(self, client, db_session):
        disc = create_discussion_with_guests(client, db_session, "已激活")
        client.post(f"/api/discussions/{disc['id']}/confirm")
        resp = client.post(f"/api/discussions/{disc['id']}/confirm")
        assert resp.status_code == 400

    def test_confirm_without_guests(self, client):
        """没有嘉宾的讨论不能确认"""
        resp = create_discussion(client, "无嘉宾")
        disc_id = resp.json()["id"]

        resp = client.post(f"/api/discussions/{disc_id}/confirm")
        assert resp.status_code == 400


class TestEndDiscussion:
    def test_end_active_discussion(self, client, db_session):
        """手动设置 active 状态后结束讨论"""
        disc = create_discussion_with_guests(client, db_session, "待结束")
        disc_id = disc["id"]
        # 手动设为 active（避免 confirm 创建后台线程）
        disc_obj = db_session.query(Discussion).filter(Discussion.id == disc_id).first()
        disc_obj.status = "active"
        db_session.commit()

        resp = client.post(f"/api/discussions/{disc_id}/end")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ended"

    def test_end_pending_discussion(self, client, db_session):
        disc = create_discussion_with_guests(client, db_session, "未开始")
        resp = client.post(f"/api/discussions/{disc['id']}/end")
        assert resp.status_code == 400


# ══════════════════════════════════════════════════════════════════
# 5. 共识与分歧查询
# ══════════════════════════════════════════════════════════════════

class TestConsensusAndDivergence:
    def test_get_empty_consensus(self, client, db_session):
        disc = create_discussion_with_guests(client, db_session)
        resp = client.get(f"/api/discussions/{disc['id']}/consensus")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_get_empty_divergence(self, client, db_session):
        disc = create_discussion_with_guests(client, db_session)
        resp = client.get(f"/api/discussions/{disc['id']}/divergence")
        assert resp.status_code == 200
        assert resp.json() == []


# ══════════════════════════════════════════════════════════════════
# 6. SSE 流
# ══════════════════════════════════════════════════════════════════

class TestSSEStream:
    @pytest.mark.skip(reason="SSE + background thread conflicts with TestClient event loop")
    def test_stream_endpoint_accepts_connection(self, client, db_session):
        """SSE 端点对已确认的讨论返回 200 + text/event-stream"""
        disc = create_discussion_with_guests(client, db_session, "SSE 测试")
        client.post(f"/api/discussions/{disc['id']}/confirm")
        with client.stream("GET", f"/api/discussions/{disc['id']}/stream") as response:
            assert response.status_code == 200
            assert "text/event-stream" in response.headers.get("content-type", "")

    @pytest.mark.skip(reason="SSE stream is long-lived; TestClient.stream iter_lines blocks")
    def test_stream_nonexistent_discussion(self, client):
        with client.stream("GET", "/api/discussions/nonexistent/stream") as response:
            assert response.status_code == 404
