from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


# ─── Discussion ──────────────────────────────────────────────

class DiscussionCreate(BaseModel):
    topic: str = Field(..., min_length=1, max_length=200, description="讨论话题")
    expert_count: int = Field(default=3, ge=1, le=10, description="专家人数（不含主持人）")
    max_rounds: int = Field(default=3, ge=1, le=10, description="最大讨论轮次")


class DiscussionResponse(BaseModel):
    id: str
    topic: str
    status: str
    expert_count: int
    host_id: Optional[str] = None
    max_rounds: int
    current_round: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class DiscussionListResponse(BaseModel):
    discussions: list[DiscussionResponse]
    total: int


class DiscussionDetailResponse(DiscussionResponse):
    guests: list[GuestResponse] = []
    speeches: list[SpeechResponse] = []


class StatusResponse(BaseModel):
    status: str


# ─── Guest ───────────────────────────────────────────────────

class GuestResponse(BaseModel):
    id: str
    discussion_id: str
    name: str
    profession: str
    title: str
    stance: str
    color: str
    role: str
    agent_state: str
    created_at: datetime

    model_config = {"from_attributes": True}


# ─── Speech ──────────────────────────────────────────────────

class SpeechResponse(BaseModel):
    id: str
    discussion_id: str
    guest_id: Optional[str] = None
    round_number: int
    content: str
    speech_type: str
    timestamp: datetime

    model_config = {"from_attributes": True}


class SpeechEvent(BaseModel):
    speech: SpeechResponse
    round_number: int


# ─── Consensus ───────────────────────────────────────────────

class ConsensusResponse(BaseModel):
    id: str
    discussion_id: str
    content: str
    supporter_guest_ids: list[str]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ConsensusEvent(BaseModel):
    consensus: ConsensusResponse


# ─── Divergence ──────────────────────────────────────────────

class DivergenceResponse(BaseModel):
    id: str
    discussion_id: str
    content: str
    opposing_pairs: list[list[str]]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class DivergenceEvent(BaseModel):
    divergence: DivergenceResponse


# ─── SSE Events ──────────────────────────────────────────────

class GuestStateEvent(BaseModel):
    guest_id: str
    agent_state: str


class DiscussionEndedEvent(BaseModel):
    discussion_id: str
    final_consensus: list[ConsensusResponse]
    final_divergence: list[DivergenceResponse]


class ErrorEvent(BaseModel):
    code: str
    message: str


# ─── Guest Generation ────────────────────────────────────────

class GenerateGuestsResponse(BaseModel):
    guests: list[GuestResponse]
