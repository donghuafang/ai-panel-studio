from sqlalchemy.orm import Session, joinedload

from backend.app.models import Discussion
from backend.app.schemas import DiscussionCreate


def create_discussion(db: Session, data: DiscussionCreate) -> Discussion:
    discussion = Discussion(
        topic=data.topic,
        expert_count=data.expert_count,
        max_rounds=data.max_rounds,
    )
    db.add(discussion)
    db.commit()
    db.refresh(discussion)
    return discussion


def get_discussion(db: Session, discussion_id: str) -> Discussion | None:
    return db.query(Discussion).filter(Discussion.id == discussion_id).first()


def list_discussions(db: Session, page: int = 1, page_size: int = 20) -> tuple[list[Discussion], int]:
    total = db.query(Discussion).count()
    discussions = (
        db.query(Discussion)
        .order_by(Discussion.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return discussions, total


def get_discussion_detail(db: Session, discussion_id: str) -> Discussion | None:
    return (
        db.query(Discussion)
        .options(
            joinedload(Discussion.guests),
            joinedload(Discussion.speeches),
        )
        .filter(Discussion.id == discussion_id)
        .first()
    )


def confirm_discussion(db: Session, discussion_id: str) -> Discussion:
    """确认嘉宾阵容，将状态从 pending 改为 active"""
    discussion = get_discussion_detail(db, discussion_id)
    if discussion is None:
        raise ValueError("讨论不存在")
    if discussion.status != "pending":
        raise ValueError(f"讨论状态为 '{discussion.status}'，无法确认")
    # 回填 host_id
    host = next((g for g in discussion.guests if g.role == "host"), None)
    if host:
        discussion.host_id = host.id
    discussion.status = "active"
    db.commit()
    db.refresh(discussion)
    return discussion


def end_discussion(db: Session, discussion_id: str) -> Discussion:
    """结束讨论，将状态从 active 改为 ended"""
    discussion = get_discussion(db, discussion_id)
    if discussion is None:
        raise ValueError("讨论不存在")
    if discussion.status != "active":
        raise ValueError(f"讨论状态为 '{discussion.status}'，无法结束")
    discussion.status = "ended"
    db.commit()
    db.refresh(discussion)
    return discussion
