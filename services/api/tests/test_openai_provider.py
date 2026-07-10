import json

import httpx
import pytest

from signaldesk.ai.base import ProviderError
from signaldesk.ai.openai import OpenAIAnalyzer
from signaldesk.config import Settings
from signaldesk.models import Case


def provider_response(text: str) -> httpx.Response:
    return httpx.Response(
        200,
        json={
            "output": [
                {
                    "type": "message",
                    "content": [{"type": "output_text", "text": text}],
                }
            ]
        },
    )


def test_openai_adapter_redacts_input_and_parses_structured_output(db):
    observed: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        observed["authorization"] = request.headers["authorization"]
        observed["body"] = json.loads(request.content)
        return provider_response(
            json.dumps(
                {
                    "summary": "External vendor transfer requires privacy review.",
                    "category": "compliance",
                    "priority": "high",
                    "risk_score": 74,
                    "confidence": 0.91,
                    "rationale": "Personal data would be sent to an external processor.",
                    "recommended_action": "Pause the transfer and obtain privacy and security approval.",
                }
            )
        )

    settings = Settings(
        ai_provider="openai",
        openai_api_key="test-key",  # pragma: allowlist secret
        openai_model="test-model",
        openai_base_url="https://provider.test/v1",
    )
    analyzer = OpenAIAnalyzer(settings, transport=httpx.MockTransport(handler))
    case = Case(
        reference="OPS-TEST-OPENAI",
        title="Vendor privacy review",
        description="Send customer records to owner@example.com for an external audit.",
        requester="Operations",
        language="en",
    )

    result = analyzer.analyze(case, db)

    request_text = observed["body"]["input"]
    assert "owner@example.com" not in request_text
    assert "<EMAIL_1>" in request_text
    assert observed["authorization"] == "Bearer test-key"
    assert observed["body"]["text"]["format"]["type"] == "json_schema"
    assert result.provider == "openai:test-model"
    assert result.category == "compliance"
    assert result.redactions[0].kind == "email"


def test_openai_adapter_returns_safe_error_for_invalid_output(db):
    analyzer = OpenAIAnalyzer(
        Settings(
            ai_provider="openai",
            openai_api_key="test-key",  # pragma: allowlist secret
            openai_base_url="https://provider.test/v1",
        ),
        transport=httpx.MockTransport(lambda _: provider_response("not-json")),
    )
    case = Case(
        reference="OPS-TEST-BAD",
        title="Review this request",
        description="Review this sufficiently detailed operational request.",
        requester="Operations",
        language="en",
    )

    with pytest.raises(ProviderError, match="invalid structured response"):
        analyzer.analyze(case, db)


def test_openai_compatible_chat_completions_mode(db):
    observed: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        observed["path"] = request.url.path
        observed["body"] = json.loads(request.content)
        content = json.dumps(
            {
                "summary": "Portal outage requires incident coordination.",
                "category": "incident",
                "priority": "high",
                "risk_score": 74,
                "confidence": 0.9,
                "rationale": "External users cannot reach the portal.",
                "recommended_action": "Assign an incident owner and confirm customer impact.",
            }
        )
        return httpx.Response(200, json={"choices": [{"message": {"content": content}}]})

    analyzer = OpenAIAnalyzer(
        Settings(
            ai_provider="openai",
            openai_api_key="test-key",  # pragma: allowlist secret
            openai_api_mode="chat_completions",
            openai_base_url="https://provider.test/inference",
            provider_label="github-models",
            openai_model="openai/gpt-4.1-mini",
        ),
        transport=httpx.MockTransport(handler),
    )
    result = analyzer.analyze(
        Case(
            reference="OPS-CHAT-1",
            title="Portal outage",
            description="The public customer portal is down and all users are blocked.",
            requester="Operations",
            language="en",
        ),
        db,
    )

    assert observed["path"].endswith("/chat/completions")
    assert observed["body"]["response_format"]["type"] == "json_schema"
    assert result.provider == "github-models:openai/gpt-4.1-mini"
    assert result.category == "incident"


def test_openai_adapter_requires_key():
    with pytest.raises(ProviderError, match="OPENAI_API_KEY"):
        OpenAIAnalyzer(Settings(ai_provider="openai", openai_api_key=None))
