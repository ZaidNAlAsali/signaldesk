import argparse
import json
import os
import subprocess
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy.orm import Session

from signaldesk.ai.openai import OpenAIAnalyzer
from signaldesk.config import Settings
from signaldesk.database import Base, make_engine
from signaldesk.models import Case
from signaldesk.seed import seed_policies


def github_token() -> str:
    token = os.getenv("GITHUB_TOKEN")
    if token:
        return token
    return subprocess.check_output(["gh", "auth", "token"], text=True).strip()


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a live, synthetic GitHub Models provider smoke test")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    settings = Settings(
        ai_provider="openai",
        openai_api_key=github_token(),
        openai_api_mode="chat_completions",
        openai_base_url="https://models.github.ai/inference",
        openai_model="openai/gpt-4.1-mini",
        provider_label="github-models",
        provider_timeout_seconds=60,
    )
    engine = make_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    fixtures = [
        Case(
            reference="SMOKE-EN",
            title="Customer portal outage",
            description="The customer portal is down and all external users are blocked after deployment.",
            requester="Synthetic smoke test",
            language="en",
        ),
        Case(
            reference="SMOKE-AR",
            title="طلب صلاحية مؤقتة",
            description="نحتاج صلاحية دخول مؤقتة إلى حساب التقارير لمدة أسبوع مع موافقة المدير.",
            requester="اختبار اصطناعي",
            language="ar",
        ),
    ]
    with Session(engine) as session:
        seed_policies(session, settings.policy_dir)
        analyzer = OpenAIAnalyzer(settings)
        results = [analyzer.analyze(case, session) for case in fixtures]

    report = {
        "verified_at_utc": datetime.now(UTC).isoformat(),
        "endpoint": "https://models.github.ai/inference/chat/completions",
        "provider": "GitHub Models",
        "requested_model": settings.openai_model,
        "synthetic_cases": [
            {
                "reference": case.reference,
                "language": case.language,
                "category": result.category.value,
                "priority": result.priority.value,
                "risk_score": result.risk_score,
                "confidence": result.confidence,
                "provider": result.provider,
                "top_policy": result.citations[0].policy_slug if result.citations else None,
            }
            for case, result in zip(fixtures, results, strict=True)
        ],
        "verified": True,
        "limitations": [
            "This smoke test verifies connectivity and schema-constrained responses for two synthetic cases.",
            "It is not a quality benchmark or availability guarantee for the external service.",
        ],
    }
    rendered = json.dumps(report, ensure_ascii=False, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)


if __name__ == "__main__":
    main()
