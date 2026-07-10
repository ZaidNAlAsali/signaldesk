from collections import Counter

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import Case, Policy
from ..retrieval import rank_policies
from ..schemas import AnalysisResult, Category, Priority
from ..security import redact_pii
from .base import Analyzer

CATEGORY_TERMS = {
    Category.INCIDENT: {"outage", "down", "breach", "incident", "failure", "تعطل", "اختراق", "حادث"},
    Category.ACCESS: {"access", "permission", "account", "login", "role", "صلاحية", "دخول", "حساب"},
    Category.PROCUREMENT: {"purchase", "vendor", "invoice", "quote", "procurement", "شراء", "مورد", "فاتورة"},
    Category.COMPLIANCE: {
        "compliance",
        "policy",
        "privacy",
        "audit",
        "regulation",
        "امتثال",
        "سياسة",
        "خصوصية",
    },
    Category.SERVICE: {"request", "support", "service", "update", "help", "طلب", "خدمة", "دعم"},
}
CRITICAL_TERMS = {"breach", "ransomware", "public outage", "safety", "اختراق", "توقف كامل", "سلامة"}
HIGH_TERMS = {"outage", "blocked", "urgent", "executive", "payment", "تعطل", "عاجل", "دفع"}


class DemoAnalyzer(Analyzer):
    def analyze(self, case: Case, session: Session) -> AnalysisResult:
        source = f"{case.title}. {case.description}"
        redacted, redactions = redact_pii(source)
        lowered = redacted.lower()
        scores = Counter()
        for category, terms in CATEGORY_TERMS.items():
            scores[category] = sum(2 if term in lowered else 0 for term in terms)
        category = scores.most_common(1)[0][0] if scores and max(scores.values()) else Category.OTHER

        if any(term in lowered for term in CRITICAL_TERMS):
            priority, risk = Priority.CRITICAL, 92
        elif any(term in lowered for term in HIGH_TERMS):
            priority, risk = Priority.HIGH, 74
        elif category in {Category.ACCESS, Category.COMPLIANCE, Category.PROCUREMENT}:
            priority, risk = Priority.MEDIUM, 52
        else:
            priority, risk = Priority.LOW, 28

        policies = list(session.scalars(select(Policy)))
        citations = rank_policies(
            f"{category.value} {redacted}",
            policies,
            category=category.value,
            language=case.language,
        )
        confidence = min(0.96, 0.62 + (scores[category] * 0.04) + (0.04 if citations else 0))
        clean_description = redacted.split(". ", 1)[-1]
        summary = clean_description[:280].strip()
        if len(clean_description) > 280:
            summary = summary.rstrip() + "..."
        action_by_category = {
            Category.INCIDENT: "Assign an incident owner, confirm impact, and begin the incident-response checklist.",
            Category.ACCESS: "Verify business need and manager approval before applying least-privilege access.",
            Category.PROCUREMENT: "Validate budget, vendor status, and required approval thresholds before commitment.",
            Category.COMPLIANCE: "Route to compliance for evidence review and record the final control decision.",
            Category.SERVICE: "Assign the relevant service owner and confirm the requested completion window.",
            Category.OTHER: "Request clarification, assign an owner, and record the final routing decision.",
        }
        rationale = (
            f"Demo analysis matched {category.value} indicators and assigned {priority.value} priority "
            f"with a {risk}/100 risk score. Explicit human review is required before any action."
        )
        return AnalysisResult(
            provider="demo-rules",
            summary=summary or case.title,
            category=category,
            priority=priority,
            risk_score=risk,
            confidence=round(confidence, 2),
            rationale=rationale,
            recommended_action=action_by_category[category],
            citations=citations,
            redactions=redactions,
        )
