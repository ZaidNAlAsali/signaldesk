import hashlib
import json
import secrets
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import Analysis, AuditEvent, Case, Decision, new_id
from .schemas import AnalysisRead, AnalysisResult, AuditRead, AuditVerificationRead, CaseRead, DecisionRequest


def generate_reference(session: Session) -> str:
    year = datetime.now(UTC).year
    for _ in range(5):
        reference = f"OPS-{year}-{secrets.token_hex(3).upper()}"
        if session.scalar(select(Case.id).where(Case.reference == reference)) is None:
            return reference
    raise RuntimeError("Could not generate a unique case reference")


def _event_digest(
    event_id: str,
    case_id: str,
    sequence: int,
    event_type: str,
    actor: str,
    payload_json: str,
    created_at: datetime,
    previous_hash: str,
) -> str:
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=UTC)
    canonical_timestamp = created_at.astimezone(UTC).isoformat(timespec="microseconds")
    canonical = json.dumps(
        {
            "id": event_id,
            "case_id": case_id,
            "sequence": sequence,
            "event_type": event_type,
            "actor": actor,
            "payload": json.loads(payload_json),
            "created_at": canonical_timestamp,
            "previous_hash": previous_hash,
        },
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def add_audit(session: Session, case_id: str, event_type: str, actor: str, payload: dict) -> AuditEvent:
    # Serialize audit appends per case on databases that support row locks.
    # SQLite ignores FOR UPDATE, while PostgreSQL prevents duplicate sequence races.
    session.execute(select(Case.id).where(Case.id == case_id).with_for_update())
    previous = session.scalar(
        select(AuditEvent).where(AuditEvent.case_id == case_id).order_by(AuditEvent.sequence.desc()).limit(1)
    )
    sequence = previous.sequence + 1 if previous else 1
    previous_hash = previous.event_hash if previous else ""
    payload_json = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    event_id = new_id()
    created_at = datetime.now(UTC)
    event_hash = _event_digest(
        event_id,
        case_id,
        sequence,
        event_type,
        actor,
        payload_json,
        created_at,
        previous_hash,
    )
    event = AuditEvent(
        id=event_id,
        case_id=case_id,
        sequence=sequence,
        event_type=event_type,
        actor=actor,
        payload_json=payload_json,
        previous_hash=previous_hash,
        event_hash=event_hash,
        created_at=created_at,
    )
    session.add(event)
    return event


def verify_audit_chain(session: Session, case_id: str) -> AuditVerificationRead:
    events = session.scalars(
        select(AuditEvent).where(AuditEvent.case_id == case_id).order_by(AuditEvent.sequence.asc())
    ).all()
    if not events:
        return AuditVerificationRead(valid=False, event_count=0, first_invalid_event_id=None)
    expected_previous = ""
    for expected_sequence, event in enumerate(events, start=1):
        expected_hash = _event_digest(
            event.id,
            event.case_id,
            event.sequence,
            event.event_type,
            event.actor,
            event.payload_json,
            event.created_at,
            event.previous_hash,
        )
        if (
            event.sequence != expected_sequence
            or event.previous_hash != expected_previous
            or event.event_hash != expected_hash
        ):
            return AuditVerificationRead(
                valid=False,
                event_count=len(events),
                first_invalid_event_id=event.id,
            )
        expected_previous = event.event_hash
    return AuditVerificationRead(valid=True, event_count=len(events))


def analysis_to_read(analysis: Analysis) -> AnalysisRead:
    return AnalysisRead(
        id=analysis.id,
        case_id=analysis.case_id,
        provider=analysis.provider,
        summary=analysis.summary,
        category=analysis.category,
        priority=analysis.priority,
        risk_score=analysis.risk_score,
        confidence=analysis.confidence,
        rationale=analysis.rationale,
        recommended_action=analysis.recommended_action,
        citations=json.loads(analysis.citations_json),
        redactions=json.loads(analysis.redactions_json),
        created_at=analysis.created_at,
    )


def case_to_read(case: Case) -> CaseRead:
    latest = max(case.analyses, key=lambda item: item.created_at) if case.analyses else None
    return CaseRead(
        id=case.id,
        reference=case.reference,
        title=case.title,
        description=case.description,
        requester=case.requester,
        language=case.language,
        category=case.category,
        priority=case.priority,
        status=case.status,
        created_at=case.created_at,
        updated_at=case.updated_at,
        latest_analysis=analysis_to_read(latest) if latest else None,
    )


def save_analysis(session: Session, case: Case, result: AnalysisResult) -> Analysis:
    locked_case = session.scalar(
        select(Case).where(Case.id == case.id).with_for_update().execution_options(populate_existing=True)
    )
    if locked_case is None:
        raise ValueError("Case no longer exists")
    if locked_case.status not in {"new", "rejected"}:
        raise ValueError("Only new or rejected cases can be analyzed")
    analysis = Analysis(
        case_id=locked_case.id,
        provider=result.provider,
        summary=result.summary,
        category=result.category.value,
        priority=result.priority.value,
        risk_score=result.risk_score,
        confidence=result.confidence,
        rationale=result.rationale,
        recommended_action=result.recommended_action,
        citations_json=json.dumps([item.model_dump() for item in result.citations], ensure_ascii=False),
        redactions_json=json.dumps([item.model_dump() for item in result.redactions], ensure_ascii=False),
    )
    locked_case.category = result.category.value
    locked_case.priority = result.priority.value
    locked_case.status = "analyzed"
    session.add(analysis)
    add_audit(
        session,
        locked_case.id,
        "case.analyzed",
        result.provider,
        {
            "category": result.category.value,
            "priority": result.priority.value,
            "risk_score": result.risk_score,
        },
    )
    session.commit()
    session.refresh(analysis)
    session.refresh(locked_case)
    return analysis


def apply_decision(session: Session, case: Case, request: DecisionRequest) -> Decision:
    locked_case = session.scalar(
        select(Case).where(Case.id == case.id).with_for_update().execution_options(populate_existing=True)
    )
    if locked_case is None:
        raise ValueError("Case no longer exists")
    if locked_case.status != "analyzed":
        raise ValueError("Only analyzed cases can receive a decision")
    status_by_action = {"approve": "approved", "override": "overridden", "reject": "rejected"}
    if request.action == "override":
        if request.category is None and request.priority is None:
            raise ValueError("Override requires a category or priority change")
        if request.category:
            locked_case.category = request.category.value
        if request.priority:
            locked_case.priority = request.priority.value
    locked_case.status = status_by_action[request.action]
    decision = Decision(case_id=locked_case.id, action=request.action, actor=request.actor, note=request.note)
    session.add(decision)
    add_audit(
        session,
        locked_case.id,
        f"case.{locked_case.status}",
        request.actor,
        {"note": request.note, "category": locked_case.category, "priority": locked_case.priority},
    )
    session.commit()
    session.refresh(decision)
    session.refresh(locked_case)
    return decision


def audit_to_read(event: AuditEvent) -> AuditRead:
    return AuditRead(
        id=event.id,
        case_id=event.case_id,
        sequence=event.sequence,
        event_type=event.event_type,
        actor=event.actor,
        payload=json.loads(event.payload_json),
        previous_hash=event.previous_hash,
        event_hash=event.event_hash,
        created_at=event.created_at,
    )
