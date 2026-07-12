from collections import Counter
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, Query, WebSocket, WebSocketDisconnect, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select, text
from sqlalchemy.orm import Session, selectinload
from starlette.concurrency import run_in_threadpool

from .ai.base import ProviderError
from .ai.factory import get_analyzer
from .config import get_settings
from .database import Base, SessionLocal, engine, get_session
from .events import manager
from .models import AuditEvent, Case, Policy
from .repository import (
    add_audit,
    analysis_to_read,
    apply_decision,
    audit_to_read,
    case_to_read,
    generate_reference,
    save_analysis,
    verify_audit_chain,
)
from .schemas import (
    AnalysisRead,
    AnalyticsRead,
    AuditRead,
    AuditVerificationRead,
    CaseCreate,
    CaseRead,
    CaseStatus,
    Category,
    DecisionRead,
    DecisionRequest,
    Priority,
)
from .seed import seed_cases, seed_policies

settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI):
    if settings.auto_create_schema:
        Base.metadata.create_all(engine)
    if settings.seed_demo_data:
        with SessionLocal() as session:
            seed_policies(session, settings.policy_dir)
            seed_cases(session)
    yield


app = FastAPI(
    title="SignalDesk API",
    version="0.3.0",
    description="Auditable, human-in-the-loop operations triage.",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)


def get_case_or_404(session: Session, case_id: str) -> Case:
    case = session.scalar(
        select(Case)
        .where(Case.id == case_id)
        .options(selectinload(Case.analyses), selectinload(Case.audit_events))
    )
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    return case


@app.get("/health")
def health() -> dict:
    return {
        "status": "ok",
        "provider": settings.ai_provider,
        "human_approval_required": True,
    }


@app.get("/ready")
def ready(session: Session = Depends(get_session)) -> dict:
    session.execute(text("SELECT 1"))
    return {"status": "ready", "database": "connected"}


@app.get("/api/cases", response_model=list[CaseRead])
def list_cases(
    status_filter: CaseStatus | None = Query(default=None, alias="status"),
    priority: Priority | None = None,
    category: Category | None = None,
    limit: int = Query(default=100, ge=1, le=500),
    session: Session = Depends(get_session),
) -> list[CaseRead]:
    query = select(Case).options(selectinload(Case.analyses)).order_by(Case.created_at.desc()).limit(limit)
    if status_filter:
        query = query.where(Case.status == status_filter.value)
    if priority:
        query = query.where(Case.priority == priority.value)
    if category:
        query = query.where(Case.category == category.value)
    return [case_to_read(case) for case in session.scalars(query).unique().all()]


@app.post("/api/cases", response_model=CaseRead, status_code=status.HTTP_201_CREATED)
async def create_case(payload: CaseCreate, session: Session = Depends(get_session)) -> CaseRead:
    case = Case(reference=generate_reference(session), **payload.model_dump())
    session.add(case)
    session.flush()
    add_audit(session, case.id, "case.created", payload.requester, {"reference": case.reference})
    session.commit()
    session.refresh(case)
    await manager.broadcast({"type": "case.created", "case_id": case.id})
    return case_to_read(case)


@app.get("/api/cases/{case_id}", response_model=CaseRead)
def get_case(case_id: str, session: Session = Depends(get_session)) -> CaseRead:
    return case_to_read(get_case_or_404(session, case_id))


@app.post("/api/cases/{case_id}/analyze", response_model=AnalysisRead)
async def analyze_case(case_id: str, session: Session = Depends(get_session)) -> AnalysisRead:
    case = get_case_or_404(session, case_id)
    if case.status not in {"new", "rejected"}:
        raise HTTPException(status_code=409, detail="Only new or rejected cases can be analyzed")
    try:
        result = await run_in_threadpool(get_analyzer(settings).analyze, case, session)
        analysis = save_analysis(session, case, result)
    except ProviderError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    await manager.broadcast({"type": "case.analyzed", "case_id": case.id})
    return analysis_to_read(analysis)


@app.post("/api/cases/{case_id}/decision", response_model=DecisionRead)
async def decide_case(
    case_id: str, payload: DecisionRequest, session: Session = Depends(get_session)
) -> DecisionRead:
    case = get_case_or_404(session, case_id)
    try:
        decision = apply_decision(session, case, payload)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    await manager.broadcast({"type": f"case.{case.status}", "case_id": case.id})
    return DecisionRead.model_validate(decision)


@app.get("/api/cases/{case_id}/audit", response_model=list[AuditRead])
def case_audit(case_id: str, session: Session = Depends(get_session)) -> list[AuditRead]:
    get_case_or_404(session, case_id)
    events = session.scalars(
        select(AuditEvent).where(AuditEvent.case_id == case_id).order_by(AuditEvent.sequence.desc())
    ).all()
    return [audit_to_read(event) for event in events]


@app.get("/api/cases/{case_id}/audit/verify", response_model=AuditVerificationRead)
def verify_case_audit(case_id: str, session: Session = Depends(get_session)) -> AuditVerificationRead:
    get_case_or_404(session, case_id)
    return verify_audit_chain(session, case_id)


@app.get("/api/policies")
def list_policies(session: Session = Depends(get_session)) -> list[dict]:
    return [
        {"slug": item.slug, "title": item.title, "category": item.category, "language": item.language}
        for item in session.scalars(
            select(Policy).order_by(Policy.category, Policy.language, Policy.title)
        ).all()
    ]


@app.get("/api/analytics", response_model=AnalyticsRead)
def analytics(session: Session = Depends(get_session)) -> AnalyticsRead:
    cases = session.scalars(select(Case).options(selectinload(Case.analyses))).unique().all()
    by_status = Counter(case.status for case in cases)
    by_priority = Counter(case.priority or "untriaged" for case in cases)
    by_category = Counter(case.category or "untriaged" for case in cases)
    latest = [max(case.analyses, key=lambda item: item.created_at) for case in cases if case.analyses]
    average = round(sum(item.confidence for item in latest) / len(latest), 2) if latest else 0.0
    high_risk_open = sum(
        1 for case in cases if case.status in {"new", "analyzed"} and case.priority in {"critical", "high"}
    )
    return AnalyticsRead(
        total=len(cases),
        by_status=dict(by_status),
        by_priority=dict(by_priority),
        by_category=dict(by_category),
        high_risk_open=high_risk_open,
        average_confidence=average,
    )


@app.websocket("/ws/events")
async def websocket_events(websocket: WebSocket):
    origin = websocket.headers.get("origin")
    if origin and origin.rstrip("/") not in settings.cors_origin_list:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
