from signaldesk.ai.demo import DemoAnalyzer
from signaldesk.models import Case


def test_demo_analysis_classifies_outage_and_cites_policy(db):
    case = Case(
        reference="OPS-TEST-1",
        title="Public portal outage",
        description="The public portal is down and executives need an urgent update.",
        requester="Operations",
        language="en",
    )
    result = DemoAnalyzer().analyze(case, db)
    assert result.category == "incident"
    assert result.priority == "high"
    assert result.risk_score >= 70
    assert result.citations[0].policy_slug == "incident-test"
    assert result.provider == "demo-rules"


def test_demo_analysis_redacts_before_summary(db):
    case = Case(
        reference="OPS-TEST-2",
        title="Privacy review",
        description="Send customer details to privacy@example.com for a compliance audit.",
        requester="Marketing",
        language="en",
    )
    result = DemoAnalyzer().analyze(case, db)
    assert "privacy@example.com" not in result.summary
    assert any(item.kind == "email" for item in result.redactions)


def test_arabic_service_request_prefers_arabic_service_policy(db):
    case = Case(
        reference="OPS-TEST-3",
        title="طلب تحديث بيانات التواصل",
        description="يرجى تحديث بيانات العميل وإرسال تأكيد بعد تنفيذ طلب الخدمة.",
        requester="خدمة العملاء",
        language="ar",
    )
    result = DemoAnalyzer().analyze(case, db)
    assert result.category == "service"
    assert result.citations[0].policy_slug == "service-test"
