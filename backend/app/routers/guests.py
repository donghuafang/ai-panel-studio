from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.app.schemas import GuestResponse, GenerateGuestsResponse
from backend.app.services.llm_client import LLMClient
from backend.app.services import guest_service

router = APIRouter(prefix="/api/discussions", tags=["guests"])


@router.post("/{discussion_id}/generate-guests", response_model=GenerateGuestsResponse)
async def generate_guests(discussion_id: str, db: Session = Depends(get_db)):
    llm = LLMClient()
    try:
        guests = await guest_service.generate_guests_for_discussion(db, llm, discussion_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"LLM 服务不可用: {str(e)}")
    return GenerateGuestsResponse(
        guests=[GuestResponse.model_validate(g) for g in guests]
    )
