import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Column, String, Integer, Text, DateTime, ForeignKey, Index, JSON
)
from sqlalchemy.orm import relationship

from app.database import Base


def _utcnow():
    return datetime.now(timezone.utc)


def _new_uuid():
    return str(uuid.uuid4())


class Discussion(Base):
    __tablename__ = "discussions"

    id = Column(String(36), primary_key=True, default=_new_uuid)
    topic = Column(String(200), nullable=False)
    status = Column(String(20), nullable=False, default="pending")  # pending | active | ended
    expert_count = Column(Integer, nullable=False, default=3)
    host_id = Column(String(36), ForeignKey("guests.id", ondelete="SET NULL"), nullable=True)
    max_rounds = Column(Integer, nullable=False, default=3)
    current_round = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), nullable=False, default=_utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow)

    guests = relationship("Guest", back_populates="discussion", foreign_keys="Guest.discussion_id")
    speeches = relationship("Speech", back_populates="discussion", cascade="all, delete-orphan")
    consensus_list = relationship("Consensus", back_populates="discussion", cascade="all, delete-orphan")
    divergence_list = relationship("Divergence", back_populates="discussion", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_discussions_status", "status"),
        Index("ix_discussions_created_at", "created_at"),
    )


class Guest(Base):
    __tablename__ = "guests"

    id = Column(String(36), primary_key=True, default=_new_uuid)
    discussion_id = Column(String(36), ForeignKey("discussions.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(100), nullable=False)
    profession = Column(String(100), nullable=False)
    title = Column(String(200), nullable=False)
    stance = Column(Text, nullable=False)
    color = Column(String(7), nullable=False)
    role = Column(String(10), nullable=False, default="guest")  # host | guest
    agent_state = Column(String(20), nullable=False, default="idle")  # idle | ready | speaking | thinking
    created_at = Column(DateTime(timezone=True), nullable=False, default=_utcnow)

    discussion = relationship("Discussion", back_populates="guests", foreign_keys=[discussion_id])
    speeches = relationship("Speech", back_populates="guest", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_guests_discussion_id", "discussion_id"),
        Index("ix_guests_role", "role"),
    )


class Speech(Base):
    __tablename__ = "speeches"

    id = Column(String(36), primary_key=True, default=_new_uuid)
    discussion_id = Column(String(36), ForeignKey("discussions.id", ondelete="CASCADE"), nullable=False)
    guest_id = Column(String(36), ForeignKey("guests.id", ondelete="SET NULL"), nullable=True)
    round_number = Column(Integer, nullable=False)
    content = Column(Text, nullable=False)
    speech_type = Column(String(20), nullable=False)  # statement | question | reply | summary
    timestamp = Column(DateTime(timezone=True), nullable=False, default=_utcnow)

    discussion = relationship("Discussion", back_populates="speeches")
    guest = relationship("Guest", back_populates="speeches")

    __table_args__ = (
        Index("ix_speeches_discussion_id", "discussion_id"),
        Index("ix_speeches_guest_id", "guest_id"),
        Index("ix_speeches_disc_round", "discussion_id", "round_number"),
    )


class Consensus(Base):
    __tablename__ = "consensus"

    id = Column(String(36), primary_key=True, default=_new_uuid)
    discussion_id = Column(String(36), ForeignKey("discussions.id", ondelete="CASCADE"), nullable=False)
    content = Column(Text, nullable=False)
    supporter_guest_ids = Column(JSON, nullable=False)  # SQLite 存为 TEXT，SQLAlchemy JSON 自动序列化
    created_at = Column(DateTime(timezone=True), nullable=False, default=_utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow)

    discussion = relationship("Discussion", back_populates="consensus_list")

    __table_args__ = (
        Index("ix_consensus_discussion_id", "discussion_id"),
    )


class Divergence(Base):
    __tablename__ = "divergence"

    id = Column(String(36), primary_key=True, default=_new_uuid)
    discussion_id = Column(String(36), ForeignKey("discussions.id", ondelete="CASCADE"), nullable=False)
    content = Column(Text, nullable=False)
    opposing_pairs = Column(JSON, nullable=False)  # [[guest_id_A, guest_id_B], ...]
    created_at = Column(DateTime(timezone=True), nullable=False, default=_utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow)

    discussion = relationship("Discussion", back_populates="divergence_list")

    __table_args__ = (
        Index("ix_divergence_discussion_id", "discussion_id"),
    )
