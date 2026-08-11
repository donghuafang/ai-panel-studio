import asyncio
import json

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from sse_starlette.sse import EventSourceResponse

from app.database import get_db
from app.models import Consensus, Divergence
from app.schemas import ConsensusResponse, DivergenceResponse
from app.services.orchestration_service import orchestrator

router = APIRouter(prefix="/api/discussions", tags=["events"])


@router.get("/{discussion_id}/stream")
async def stream_discussion(discussion_id: str, request: Request):
    """SSE 实时事件流"""
    queue = orchestrator.subscribe(discussion_id)

    async def event_generator():
        try:
            while True:
                if await request.is_disconnected():
                    break
                try:
                    event_data = await asyncio.wait_for(queue.get(), timeout=15.0)
                    yield {
                        "event": event_data["event"],
                        "data": event_data["data"],
                    }
                except asyncio.TimeoutError:
                    # 发送心跳保持连接
                    yield {"event": "ping", "data": "{}"}
        finally:
            orchestrator.unsubscribe(discussion_id, queue)

    return EventSourceResponse(event_generator())


@router.get("/{discussion_id}/consensus", response_model=list[ConsensusResponse])
def get_consensus_list(discussion_id: str, db: Session = Depends(get_db)):
    items = db.query(Consensus).filter(Consensus.discussion_id == discussion_id).all()
    return [ConsensusResponse.model_validate(c) for c in items]


@router.get("/{discussion_id}/divergence", response_model=list[DivergenceResponse])
def get_divergence_list(discussion_id: str, db: Session = Depends(get_db)):
    items = db.query(Divergence).filter(Divergence.discussion_id == discussion_id).all()
    return [DivergenceResponse.model_validate(d) for d in items]
