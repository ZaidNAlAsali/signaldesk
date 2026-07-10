from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint, event
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


def now_utc() -> datetime:
    return datetime.now(UTC)


def new_id() -> str:
    return str(uuid4())


class Case(Base):
    __tablename__ = "cases"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    reference: Mapped[str] = mapped_column(String(24), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(180))
    description: Mapped[str] = mapped_column(Text)
    requester: Mapped[str] = mapped_column(String(120))
    language: Mapped[str] = mapped_column(String(8), default="en")
    category: Mapped[str | None] = mapped_column(String(40), nullable=True, index=True)
    priority: Mapped[str | None] = mapped_column(String(20), nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(24), default="new", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, onupdate=now_utc)

    analyses: Mapped[list[Analysis]] = relationship(back_populates="case", cascade="all, delete-orphan")
    decisions: Mapped[list[Decision]] = relationship(back_populates="case", cascade="all, delete-orphan")
    audit_events: Mapped[list[AuditEvent]] = relationship(back_populates="case", cascade="all, delete-orphan")


class Analysis(Base):
    __tablename__ = "analyses"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    case_id: Mapped[str] = mapped_column(ForeignKey("cases.id"), index=True)
    provider: Mapped[str] = mapped_column(String(30))
    summary: Mapped[str] = mapped_column(Text)
    category: Mapped[str] = mapped_column(String(40))
    priority: Mapped[str] = mapped_column(String(20))
    risk_score: Mapped[int] = mapped_column(Integer)
    confidence: Mapped[float] = mapped_column(Float)
    rationale: Mapped[str] = mapped_column(Text)
    recommended_action: Mapped[str] = mapped_column(Text)
    citations_json: Mapped[str] = mapped_column(Text, default="[]")
    redactions_json: Mapped[str] = mapped_column(Text, default="[]")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)

    case: Mapped[Case] = relationship(back_populates="analyses")


class Decision(Base):
    __tablename__ = "decisions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    case_id: Mapped[str] = mapped_column(ForeignKey("cases.id"), index=True)
    action: Mapped[str] = mapped_column(String(24))
    actor: Mapped[str] = mapped_column(String(120))
    note: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)

    case: Mapped[Case] = relationship(back_populates="decisions")


class AuditEvent(Base):
    __tablename__ = "audit_events"
    __table_args__ = (UniqueConstraint("case_id", "sequence", name="uq_audit_case_sequence"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    case_id: Mapped[str] = mapped_column(ForeignKey("cases.id"), index=True)
    sequence: Mapped[int] = mapped_column(Integer)
    event_type: Mapped[str] = mapped_column(String(50), index=True)
    actor: Mapped[str] = mapped_column(String(120))
    payload_json: Mapped[str] = mapped_column(Text, default="{}")
    previous_hash: Mapped[str] = mapped_column(String(64), default="")
    event_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)

    case: Mapped[Case] = relationship(back_populates="audit_events")


class Policy(Base):
    __tablename__ = "policies"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    slug: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(180))
    category: Mapped[str] = mapped_column(String(40), index=True)
    language: Mapped[str] = mapped_column(String(8), default="en")
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)


@event.listens_for(AuditEvent, "before_update")
def prevent_audit_update(*_: object) -> None:
    raise ValueError("Audit events are append-only and cannot be updated")


@event.listens_for(AuditEvent, "before_delete")
def prevent_audit_delete(*_: object) -> None:
    raise ValueError("Audit events are append-only and cannot be deleted")
