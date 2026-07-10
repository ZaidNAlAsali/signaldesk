import argparse
import json
import platform
import statistics
import time
from pathlib import Path

from sqlalchemy.orm import Session

from signaldesk.ai.demo import DemoAnalyzer
from signaldesk.config import Settings
from signaldesk.database import Base, make_engine
from signaldesk.models import Case
from signaldesk.seed import seed_policies


def percentile(values: list[float], quantile: float) -> float:
    ordered = sorted(values)
    index = min(len(ordered) - 1, round((len(ordered) - 1) * quantile))
    return ordered[index]


def benchmark(iterations: int, repeats: int) -> dict:
    engine = make_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    analyzer = DemoAnalyzer()
    samples = [
        (
            "en",
            "Customer portal outage",
            "The public portal is down and users are blocked after deployment. Contact owner@example.com.",
        ),
        (
            "ar",
            "طلب صلاحية مؤقتة",
            "نحتاج صلاحية دخول مؤقتة إلى حساب التقارير لمدة أسبوع.",
        ),
        (
            "en",
            "Privacy review",
            "A vendor will process customer data and requires a privacy compliance review.",
        ),
    ]
    latencies_ms: list[float] = []
    repeat_throughput: list[float] = []

    with Session(engine) as session:
        seed_policies(session, Settings().policy_dir)
        for index in range(50):
            language, title, description = samples[index % len(samples)]
            analyzer.analyze(
                Case(
                    reference=f"WARM-{index}",
                    title=title,
                    description=description,
                    requester="Bench",
                    language=language,
                ),
                session,
            )
        for repeat in range(repeats):
            start_repeat = time.perf_counter()
            for index in range(iterations):
                language, title, description = samples[index % len(samples)]
                case = Case(
                    reference=f"BENCH-{repeat}-{index}",
                    title=title,
                    description=description,
                    requester="Benchmark fixture",
                    language=language,
                )
                start = time.perf_counter()
                analyzer.analyze(case, session)
                latencies_ms.append((time.perf_counter() - start) * 1000)
            elapsed = time.perf_counter() - start_repeat
            repeat_throughput.append(iterations / elapsed)

    return {
        "benchmark": "SignalDesk deterministic triage pipeline",
        "scope": "PII redaction, keyword classification, policy retrieval, and Pydantic validation; excludes HTTP and persistence",
        "iterations_per_repeat": iterations,
        "repeats": repeats,
        "total_operations": iterations * repeats,
        "results": {
            "throughput_ops_per_second_median": round(statistics.median(repeat_throughput), 2),
            "throughput_ops_per_second_min": round(min(repeat_throughput), 2),
            "latency_ms_p50": round(percentile(latencies_ms, 0.50), 4),
            "latency_ms_p95": round(percentile(latencies_ms, 0.95), 4),
            "latency_ms_p99": round(percentile(latencies_ms, 0.99), 4),
        },
        "environment": {
            "python": platform.python_version(),
            "platform": platform.platform(),
            "processor": platform.processor() or "not reported",
        },
        "limitations": [
            "Results describe deterministic local analysis only and are not external-provider latency.",
            "Hardware, power state, and background workload affect results.",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--iterations", type=int, default=1000)
    parser.add_argument("--repeats", type=int, default=5)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.iterations < 1 or args.repeats < 1:
        parser.error("iterations and repeats must be positive")
    result = benchmark(args.iterations, args.repeats)
    rendered = json.dumps(result, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)


if __name__ == "__main__":
    main()
