from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .models import Case, Policy
from .repository import add_audit

DEMO_CASES = [
    {
        "reference": "OPS-2026-0001",
        "title": "Customer portal unavailable after deployment",
        "description": "The public customer portal is down for all users after the 09:30 deployment. Support has received 41 calls and executives requested an urgent update.",
        "requester": "Digital Services",
        "language": "en",
    },
    {
        "reference": "OPS-2026-0002",
        "title": "طلب صلاحية مؤقتة لنظام المشتريات",
        "description": "نحتاج صلاحية مؤقتة لموظف جديد للوصول إلى نظام المشتريات ومراجعة فواتير الموردين قبل نهاية اليوم.",
        "requester": "فريق العمليات",
        "language": "ar",
    },
    {
        "reference": "OPS-2026-0003",
        "title": "New analytics vendor requires privacy review",
        "description": "The marketing team wants to upload customer contact records to a new analytics vendor. Contact: privacy.owner@example.com, +974 5555 0101.",
        "requester": "Marketing Operations",
        "language": "en",
    },
    {
        "reference": "OPS-2026-0004",
        "title": "Emergency purchase request for network equipment",
        "description": "A branch has requested an urgent direct purchase from a new vendor after repeated router failures. The quotation exceeds the normal team approval limit.",
        "requester": "Infrastructure",
        "language": "en",
    },
    {
        "reference": "OPS-2026-0005",
        "title": "Unable to access monthly service dashboard",
        "description": "A regional manager cannot log in to the service dashboard after changing devices and needs access before the weekly review.",
        "requester": "Service Delivery",
        "language": "en",
    },
    {
        "reference": "OPS-2026-0006",
        "title": "طلب تحديث بيانات التواصل",
        "description": "يرجى تحديث رقم التواصل والبريد الإلكتروني في نظام خدمة العملاء وإرسال تأكيد بعد إكمال الطلب.",
        "requester": "خدمة العملاء",
        "language": "ar",
    },
]


def seed_policies(session: Session, policy_dir: Path) -> None:
    if (session.scalar(select(func.count()).select_from(Policy)) or 0) > 0:
        return
    for path in sorted(policy_dir.glob("*.md")):
        parts = path.stem.split("__", 2)
        category = parts[0]
        language = parts[1] if len(parts) > 1 else "en"
        content = path.read_text(encoding="utf-8")
        lines = content.splitlines()
        title = lines[0].lstrip("# ").strip()
        body = "\n".join(lines[1:]).strip()
        session.add(Policy(slug=path.stem, title=title, category=category, language=language, content=body))
    session.commit()


def seed_cases(session: Session) -> None:
    if (session.scalar(select(func.count()).select_from(Case)) or 0) > 0:
        return
    for item in DEMO_CASES:
        case = Case(**item)
        session.add(case)
        session.flush()
        add_audit(session, case.id, "case.created", item["requester"], {"reference": item["reference"]})
    session.commit()
