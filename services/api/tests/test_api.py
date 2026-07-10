def create_case(client):
    response = client.post(
        "/api/cases",
        json={
            "title": "Portal outage after release",
            "description": "The customer portal is down and the issue is urgent.",
            "requester": "Operations",
            "language": "en",
        },
    )
    assert response.status_code == 201
    return response.json()


def test_full_human_in_the_loop_workflow(client):
    case = create_case(client)
    analysis_response = client.post(f"/api/cases/{case['id']}/analyze")
    assert analysis_response.status_code == 200
    analysis = analysis_response.json()
    assert analysis["priority"] == "high"
    assert client.post(f"/api/cases/{case['id']}/analyze").status_code == 409

    decision_response = client.post(
        f"/api/cases/{case['id']}/decision",
        json={"action": "approve", "actor": "Demo reviewer", "note": "Validated incident impact."},
    )
    assert decision_response.status_code == 200
    duplicate_decision = client.post(
        f"/api/cases/{case['id']}/decision",
        json={"action": "reject", "actor": "Demo reviewer", "note": "Conflicting decision."},
    )
    assert duplicate_decision.status_code == 409

    updated = client.get(f"/api/cases/{case['id']}").json()
    assert updated["status"] == "approved"

    audit = client.get(f"/api/cases/{case['id']}/audit").json()
    assert [item["event_type"] for item in audit] == [
        "case.approved",
        "case.analyzed",
        "case.created",
    ]


def test_override_requires_change(client):
    case = create_case(client)
    client.post(f"/api/cases/{case['id']}/analyze")
    response = client.post(
        f"/api/cases/{case['id']}/decision",
        json={"action": "override", "actor": "Reviewer", "note": "No actual change"},
    )
    assert response.status_code == 409
