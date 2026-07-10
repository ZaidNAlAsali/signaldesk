from starlette.websockets import WebSocketDisconnect


def test_websocket_broadcasts_case_creation(client):
    with client.websocket_connect("/ws/events", headers={"origin": "http://localhost:3000"}) as socket:
        response = client.post(
            "/api/cases",
            json={
                "title": "Realtime workflow test",
                "description": "Verify that a new request is broadcast to connected reviewers.",
                "requester": "QA",
                "language": "en",
            },
        )
        assert response.status_code == 201
        event = socket.receive_json()
        assert event == {"type": "case.created", "case_id": response.json()["id"]}


def test_websocket_rejects_untrusted_browser_origin(client):
    try:
        with client.websocket_connect("/ws/events", headers={"origin": "https://attacker.example"}):
            raise AssertionError("Untrusted origin was accepted")
    except WebSocketDisconnect as exc:
        assert exc.code == 1008
