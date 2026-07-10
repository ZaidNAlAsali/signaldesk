from signaldesk.security import redact_pii


def test_redacts_email_phone_and_card():
    text = "Email me at owner@example.com or +974 5555 0101. Card 4111 1111 1111 1111."
    redacted, findings = redact_pii(text)
    assert "owner@example.com" not in redacted
    assert "+974 5555 0101" not in redacted
    assert "4111 1111 1111 1111" not in redacted
    assert {item.kind for item in findings} == {"email", "phone", "payment_card"}
