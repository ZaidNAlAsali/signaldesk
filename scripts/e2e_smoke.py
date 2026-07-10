# /// script
# requires-python = ">=3.11"
# dependencies = ["websockets>=15.0.1"]
# ///

import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any

from websockets.sync.client import connect

API_URL = os.getenv("SIGNALDESK_API_URL", "http://127.0.0.1:8000").rstrip("/")
WS_URL = os.getenv("SIGNALDESK_WS_URL", "ws://127.0.0.1:8000/ws/events")
ORIGIN = os.getenv("SIGNALDESK_ORIGIN", "http://localhost:3000")


@dataclass
class APIError(RuntimeError):
    status: int
    body: str


def request(method: str, path: str, payload: dict | None = None) -> Any:
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8") if payload is not None else None
    req = urllib.request.Request(
        f"{API_URL}{path}",
        data=data,
        method=method,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raise APIError(exc.code, exc.read().decode("utf-8")) from exc


def create_case(title: str, description: str, requester: str, language: str) -> dict:
    return request(
        "POST",
        "/api/cases",
        {"title": title, "description": description, "requester": requester, "language": language},
    )


def verify_audit(case_id: str, expected_minimum: int) -> dict:
    verification = request("GET", f"/api/cases/{case_id}/audit/verify")
    assert verification["valid"] is True, verification
    assert verification["event_count"] >= expected_minimum, verification
    return verification


def main() -> None:
    assert request("GET", "/health")["status"] == "ok"
    assert request("GET", "/ready")["database"] == "connected"

    with connect(WS_URL, origin=ORIGIN, open_timeout=10, close_timeout=5) as socket:
        realtime = create_case(
            "Realtime workflow verification",
            "Verify that connected reviewers receive a case-created event through WebSockets.",
            "E2E QA",
            "en",
        )
        event = json.loads(socket.recv(timeout=10))
        assert event == {"type": "case.created", "case_id": realtime["id"]}, event

    english = create_case(
        "Customer portal outage",
        "The customer portal is down and all external users are blocked after deployment.",
        "Digital Services",
        "en",
    )
    english_analysis = request("POST", f"/api/cases/{english['id']}/analyze")
    assert english_analysis["category"] == "incident", english_analysis
    assert english_analysis["priority"] in {"critical", "high"}, english_analysis
    assert english_analysis["citations"][0]["policy_slug"].startswith("incident__en"), english_analysis
    request(
        "POST",
        f"/api/cases/{english['id']}/decision",
        {"action": "approve", "actor": "E2E Reviewer", "note": "Impact and owner verified."},
    )
    english_audit = verify_audit(english["id"], 3)

    arabic = create_case(
        "طلب صلاحية مؤقتة",
        "نحتاج صلاحية دخول مؤقتة إلى حساب التقارير لمدة أسبوع مع موافقة المدير.",
        "فريق العمليات",
        "ar",
    )
    arabic_analysis = request("POST", f"/api/cases/{arabic['id']}/analyze")
    assert arabic_analysis["category"] == "access", arabic_analysis
    assert arabic_analysis["citations"][0]["policy_slug"].startswith("access__ar"), arabic_analysis
    request(
        "POST",
        f"/api/cases/{arabic['id']}/decision",
        {
            "action": "override",
            "actor": "E2E Reviewer",
            "note": "Escalated for the requested time window.",
            "priority": "high",
        },
    )
    arabic_audit = verify_audit(arabic["id"], 3)

    rejected = create_case(
        "Update service contact",
        "Please update the service contact record after requester verification.",
        "Customer Service",
        "en",
    )
    request("POST", f"/api/cases/{rejected['id']}/analyze")
    request(
        "POST",
        f"/api/cases/{rejected['id']}/decision",
        {"action": "reject", "actor": "E2E Reviewer", "note": "Requester identity was not verified."},
    )
    rejected_audit = verify_audit(rejected["id"], 3)

    output = {
        "status": "passed",
        "provider": english_analysis["provider"],
        "workflows": ["websocket", "english-approve", "arabic-override", "reject"],
        "audit_events_verified": (
            english_audit["event_count"] + arabic_audit["event_count"] + rejected_audit["event_count"]
        ),
    }
    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
