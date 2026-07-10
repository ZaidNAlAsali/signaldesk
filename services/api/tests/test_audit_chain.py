import pytest
from sqlalchemy import text

from signaldesk.models import AuditEvent, Case
from signaldesk.repository import add_audit, verify_audit_chain


def create_case(db) -> Case:
    case = Case(
        reference="OPS-AUDIT-1",
        title="Audit chain test",
        description="A sufficiently detailed request used to test audit history.",
        requester="QA",
        language="en",
    )
    db.add(case)
    db.flush()
    return case


def test_audit_chain_is_valid_and_detects_database_tampering(db):
    case = create_case(db)
    add_audit(db, case.id, "case.created", "QA", {"reference": case.reference})
    add_audit(db, case.id, "case.analyzed", "demo-rules", {"risk_score": 25})
    db.commit()

    result = verify_audit_chain(db, case.id)
    assert result.valid is True
    assert result.event_count == 2

    db.execute(
        text("UPDATE audit_events SET payload_json = :payload WHERE sequence = 2"),
        {"payload": '{"risk_score":99}'},
    )
    db.commit()
    tampered = verify_audit_chain(db, case.id)
    assert tampered.valid is False
    assert tampered.first_invalid_event_id is not None


def test_audit_events_cannot_be_updated_or_deleted_through_orm(db):
    case = create_case(db)
    event = add_audit(db, case.id, "case.created", "QA", {})
    db.commit()

    event.actor = "Changed"
    with pytest.raises(ValueError, match="append-only"):
        db.commit()
    db.rollback()

    persisted = db.get(AuditEvent, event.id)
    db.delete(persisted)
    with pytest.raises(ValueError, match="append-only"):
        db.commit()
