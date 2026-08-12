"""pytest fixtures for AI Panel Studio tests.

Provides mock LLM client, in-memory SQLite database, and sample data fixtures.
All tests can run without network or API key.
"""

import pytest
from unittest.mock import MagicMock, AsyncMock
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.models import Discussion, Guest, Speech


# ── In-memory SQLite engine ─────────────────────────────────────

@pytest.fixture(scope="function")
def db_session():
    """Create a fresh in-memory SQLite database for each test.

    Uses StaticPool to enforce a single connection — SQLite :memory:
    otherwise creates a new DB per connection.
    """
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=False,
    )

    # Enable foreign keys
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


# ── Mock LLM Client ──────────────────────────────────────────────

@pytest.fixture
def mock_llm_client():
    """Return a MagicMock standing in for LLMClient.

    All async methods are AsyncMock instances so they can be awaited.
    Tests configure return values per scenario.
    """
    mock = MagicMock()
    mock.chat_completion = AsyncMock()
    mock.generate_guests = AsyncMock()
    mock.generate_speech = AsyncMock()
    return mock


# ── Sample Data ──────────────────────────────────────────────────

@pytest.fixture
def sample_discussion(db_session):
    """Create a pending Discussion with 3 experts, 3 rounds."""
    disc = Discussion(
        topic="AI 会取代人类创造力吗",
        status="pending",
        expert_count=3,
        max_rounds=3,
    )
    db_session.add(disc)
    db_session.commit()
    db_session.refresh(disc)
    return disc


@pytest.fixture
def sample_discussion_active(db_session):
    """Create an active Discussion with 3 experts, 3 rounds."""
    disc = Discussion(
        topic="AI 会取代人类创造力吗",
        status="active",
        expert_count=3,
        max_rounds=3,
        current_round=1,
    )
    db_session.add(disc)
    db_session.commit()
    db_session.refresh(disc)
    return disc


@pytest.fixture
def sample_guests(db_session, sample_discussion):
    """Create 1 host + 3 expert guests for the sample discussion."""
    host = Guest(
        discussion_id=sample_discussion.id,
        name="张明",
        profession="科技媒体主编",
        title="资深科技评论员",
        stance="中立，客观引导讨论",
        color="#4A90D9",
        role="host",
        agent_state="ready",
    )
    expert_a = Guest(
        discussion_id=sample_discussion.id,
        name="李伟",
        profession="软件工程师",
        title="资深全栈开发者",
        stance="AI 将大幅提升编程效率，但创造力仍是人类核心优势",
        color="#FF6B6B",
        role="guest",
        agent_state="ready",
    )
    expert_b = Guest(
        discussion_id=sample_discussion.id,
        name="王芳",
        profession="AI 研究员",
        title="机器学习博士",
        stance="AI 最终将在大多数创造性任务上超越人类",
        color="#4ECDC4",
        role="guest",
        agent_state="ready",
    )
    expert_c = Guest(
        discussion_id=sample_discussion.id,
        name="赵强",
        profession="企业家",
        title="创业公司 CEO",
        stance="AI 是工具，关键在于人类如何利用它创造价值",
        color="#45B7D1",
        role="guest",
        agent_state="ready",
    )

    db_session.add_all([host, expert_a, expert_b, expert_c])
    db_session.commit()
    for g in [host, expert_a, expert_b, expert_c]:
        db_session.refresh(g)

    return {
        "host": host,
        "experts": [expert_a, expert_b, expert_c],
        "all": [host, expert_a, expert_b, expert_c],
    }


@pytest.fixture
def sample_speeches(db_session, sample_discussion, sample_guests):
    """Create 5 speeches: host opening, 3 expert statements, host summary (round 1)."""
    host = sample_guests["host"]
    experts = sample_guests["experts"]

    speeches_data = [
        (host.id, 1, "欢迎大家来到今天的圆桌讨论，今天我们讨论 AI 与人类创造力的关系。", "statement"),
        (experts[0].id, 1, "我认为 AI 是强大的辅助工具，但真正的创意突破仍然需要人类的直觉和经验。", "statement"),
        (experts[1].id, 1, "从技术发展来看，生成式 AI 已经能创作音乐和绘画，人类的创造力优势正在缩小。", "statement"),
        (experts[2].id, 1, "关键不是 AI 是否会取代人，而是我们如何重新定义人与 AI 的协作方式。", "statement"),
        (host.id, 1, "本轮讨论中，我们听到了不同的观点，下一轮我们将深入探讨具体案例。", "summary"),
    ]

    speeches = []
    for guest_id, round_num, content, speech_type in speeches_data:
        s = Speech(
            discussion_id=sample_discussion.id,
            guest_id=guest_id,
            round_number=round_num,
            content=content,
            speech_type=speech_type,
        )
        db_session.add(s)
        speeches.append(s)

    db_session.commit()
    for s in speeches:
        db_session.refresh(s)
    return speeches
