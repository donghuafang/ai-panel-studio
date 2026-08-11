from sqlalchemy.orm import Session

from backend.app.models import Discussion, Guest
from backend.app.services.llm_client import LLMClient


async def generate_guests_for_discussion(
    db: Session,
    llm: LLMClient,
    discussion_id: str,
) -> list[Guest]:
    """调用 LLM 生成嘉宾阵容并写入数据库"""
    discussion = db.query(Discussion).filter(Discussion.id == discussion_id).first()
    if discussion is None:
        raise ValueError("讨论不存在")
    if discussion.status != "pending":
        raise ValueError("讨论状态不允许生成嘉宾")

    # 清除旧嘉宾（如果重新生成）
    db.query(Guest).filter(Guest.discussion_id == discussion_id).delete()

    # 调用 LLM
    guest_dicts = await llm.generate_guests(discussion.topic, discussion.expert_count)

    # 写入数据库
    guests = []
    for gd in guest_dicts:
        guest = Guest(
            discussion_id=discussion_id,
            name=gd["name"],
            profession=gd["profession"],
            title=gd["title"],
            stance=gd["stance"],
            color=gd["color"],
            role=gd.get("role", "guest"),
            agent_state="ready",
        )
        db.add(guest)
        guests.append(guest)

    db.commit()
    for g in guests:
        db.refresh(g)
    return guests
