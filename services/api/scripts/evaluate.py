import argparse
import json
from collections import Counter
from pathlib import Path

from sqlalchemy.orm import Session

from signaldesk.ai.demo import DemoAnalyzer
from signaldesk.config import Settings
from signaldesk.database import Base, make_engine
from signaldesk.models import Case
from signaldesk.seed import seed_policies


def load_cases(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def evaluate(dataset: Path) -> dict:
    engine = make_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    analyzer = DemoAnalyzer()
    settings = Settings()
    rows = load_cases(dataset)
    totals = Counter()
    language = {"en": Counter(), "ar": Counter()}
    failures: list[dict] = []

    with Session(engine) as session:
        seed_policies(session, settings.policy_dir)
        for row in rows:
            case = Case(
                reference=f"EVAL-{row['id']}",
                title=row["title"],
                description=row["description"],
                requester="Evaluation fixture",
                language=row["language"],
            )
            result = analyzer.analyze(case, session)
            category_ok = result.category.value == row["expected_category"]
            priority_ok = result.priority.value == row["expected_priority"]
            policy_ok = row["expected_category"] == "other" or (
                bool(result.citations)
                and result.citations[0].policy_slug.startswith(row["expected_category"])
            )
            redaction_ok = not row.get("expected_redaction") or any(
                item.kind == row["expected_redaction"] for item in result.redactions
            )
            for key, ok in {
                "category_correct": category_ok,
                "priority_correct": priority_ok,
                "joint_correct": category_ok and priority_ok,
                "policy_top1_correct": policy_ok,
                "redaction_correct": redaction_ok,
            }.items():
                totals[key] += int(ok)
                language[row["language"]][key] += int(ok)
            if not all((category_ok, priority_ok, policy_ok, redaction_ok)):
                failures.append(
                    {
                        "id": row["id"],
                        "expected": {
                            "category": row["expected_category"],
                            "priority": row["expected_priority"],
                        },
                        "actual": {
                            "category": result.category.value,
                            "priority": result.priority.value,
                            "top_policy": result.citations[0].policy_slug if result.citations else None,
                        },
                    }
                )

    count = len(rows)

    def metrics(counter: Counter, denominator: int) -> dict:
        return {
            key.replace("_correct", "_accuracy"): round(counter[key] / denominator, 4)
            for key in (
                "category_correct",
                "priority_correct",
                "joint_correct",
                "policy_top1_correct",
                "redaction_correct",
            )
        }

    language_counts = Counter(row["language"] for row in rows)
    return {
        "evaluation": "SignalDesk deterministic demo triage",
        "dataset": dataset.name,
        "case_count": count,
        "metrics": metrics(totals, count),
        "by_language": {
            code: {"case_count": language_counts[code], **metrics(counter, language_counts[code])}
            for code, counter in language.items()
        },
        "failures": failures,
        "limitations": [
            "This is a small, authored regression set, not an estimate of production model quality.",
            "The deterministic analyzer is designed for reproducible demos and tests, not semantic generalization.",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=Path, default=Path("eval/cases.jsonl"))
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = evaluate(args.dataset)
    rendered = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)


if __name__ == "__main__":
    main()
