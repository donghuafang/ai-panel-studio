import threading
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.app.schemas import (
    DiscussionCreate,
    DiscussionResponse,
    DiscussionListResponse,
    DiscussionDetailResponse,
    StatusResponse,
)
from backend.app.services import discussion_service
from backend.app.services.orchestration_service import orchestrator

router = APIRouter(prefix="/api/discussions", tags=["discussions"])


@router.get("", response_model=DiscussionListResponse)
def list_discussions(page: int = 1, page_size: int = 20, db: Session = Depends(get_db)):
    discussions, total = discussion_service.list_discussions(db, page, page_size)
    return DiscussionListResponse(
        discussions=[DiscussionResponse.model_validate(d) for d in discussions],
        total=total,
    )


@router.post("", response_model=DiscussionResponse, status_code=201)
def create_discussion(data: DiscussionCreate, db: Session = Depends(get_db)):
    discussion = discussion_service.create_discussion(db, data)
    return DiscussionResponse.model_validate(discussion)


@router.get("/{discussion_id}", response_model=DiscussionDetailResponse)
def get_discussion(discussion_id: str, db: Session = Depends(get_db)):
    discussion = discussion_service.get_discussion_detail(db, discussion_id)
    if discussion is None:
        raise HTTPException(status_code=404, detail="讨论不存在")
    return DiscussionDetailResponse.model_validate(discussion)


@router.post("/{discussion_id}/confirm", response_model=StatusResponse)
def confirm_discussion(discussion_id: str, db: Session = Depends(get_db)):
    try:
        discussion = discussion_service.confirm_discussion(db, discussion_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # 启动后台编排
    from backend.app.database import SessionLocal
    thread = threading.Thread(
        target=orchestrator.run_discussion,
        args=(SessionLocal, discussion_id),
        daemon=True,
    )
    thread.start()

    return StatusResponse(status=discussion.status)


@router.post("/{discussion_id}/end", response_model=StatusResponse)
def end_discussion(discussion_id: str, db: Session = Depends(get_db)):
    try:
        discussion = discussion_service.end_discussion(db, discussion_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return StatusResponse(status=discussion.status)
