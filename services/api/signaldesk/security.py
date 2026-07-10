import re
from dataclasses import dataclass

from .schemas import Redaction


@dataclass(frozen=True)
class Pattern:
    kind: str
    regex: re.Pattern[str]


PATTERNS = [
    Pattern("email", re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)),
    Pattern("payment_card", re.compile(r"(?<!\d)(?:\d[ -]*?){13,19}(?!\d)")),
    Pattern("phone", re.compile(r"(?<!\w)(?:\+?\d[\d\s().-]{7,}\d)(?!\w)")),
    Pattern("id_number", re.compile(r"\b(?:QID|ID|هوية)[:\s#-]*[A-Z0-9-]{6,20}\b", re.IGNORECASE)),
]


def redact_pii(text: str) -> tuple[str, list[Redaction]]:
    redacted = text
    findings: list[Redaction] = []
    counters: dict[str, int] = {}
    for pattern in PATTERNS:
        kind = pattern.kind

        def replace(match: re.Match[str], kind: str = kind) -> str:
            counters[kind] = counters.get(kind, 0) + 1
            placeholder = f"<{kind.upper()}_{counters[kind]}>"
            findings.append(Redaction(kind=kind, placeholder=placeholder))
            return placeholder

        redacted = pattern.regex.sub(replace, redacted)
    return redacted, findings
