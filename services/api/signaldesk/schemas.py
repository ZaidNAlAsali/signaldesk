from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class Category(StrEnum):
    INCIDENT = "incident"
    ACCESS = "access"
    PROCUREMENT = "procurement"
    COMPLIANCE = "compliance"
    SERVICE = "service"
    OTHER = "other"


class Priority(StrEnum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class CaseStatus(StrEnum):
    NEW = "new"
    ANALYZED = "analyzed"
    APPROVED = "approved"
    OVERRIDDEN = "overridden"
    REJECTED = "rejected"


class Citation(BaseModel):
    policy_slug: str
    policy_title: str
    excerpt: str
    score: float = Field(ge=0)


class Redaction(BaseModel):
    kind: str
    placeholder: str


class AnalysisResult(BaseModel):
    provider: str
    summary: str = Field(min_length=10, max_length=600)
    category: Category
    priority: Priority
    risk_score: int = Field(ge=0, le=100)
    confidence: float = Field(ge=0, le=1)
    rationale: str = Field(min_length=10, max_length=1000)
    recommended_action: str = Field(min_length=10, max_length=1000)
    citations: list[Citation] = Field(default_factory=list)
    redactions: list[Redaction] = Field(default_factory=list)


class CaseCreate(BaseModel):
    title: str = Field(min_length=4, max_length=180)
    description: str = Field(min_length=10, max_length=6000)
    requester: str = Field(min_length=2, max_length=120)
    language: str = Field(default="en", pattern="^(en|ar)$")


class AnalysisRead(AnalysisResult):
    model_config = ConfigDict(from_attributes=True)
    id: str
    case_id: str
    created_at: datetime


class DecisionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    case_id: str
    action: str
    actor: str
    note: str
    created_at: datetime


class AuditRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    case_id: str
    sequence: int
    event_type: str
    actor: str
    payload: dict
    previous_hash: str
    event_hash: str
    created_at: datetime


class AuditVerificationRead(BaseModel):
    valid: bool
    event_count: int
    first_invalid_event_id: str | None = None


class CaseRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    reference: str
    title: str
    description: str
    requester: str
    language: str
    category: str | None
    priority: str | None
    status: str
    created_at: datetime
    updated_at: datetime
    latest_analysis: AnalysisRead | None = None


class DecisionRequest(BaseModel):
    action: str = Field(pattern="^(approve|override|reject)$")
    actor: str = Field(min_length=2, max_length=120)
    note: str = Field(default="", max_length=1200)
    category: Category | None = None
    priority: Priority | None = None


class AnalyticsRead(BaseModel):
    total: int
    by_status: dict[str, int]
    by_priority: dict[str, int]
    by_category: dict[str, int]
    high_risk_open: int
    average_confidence: float
