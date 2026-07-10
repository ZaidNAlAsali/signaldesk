import math
import re
from dataclasses import dataclass

from .models import Policy
from .schemas import Citation

TOKEN_RE = re.compile(r"[\w؀-ۿ]+", re.UNICODE)
STOP = {"the", "and", "for", "with", "this", "that", "from", "into", "على", "من", "في", "إلى", "و"}


@dataclass(frozen=True)
class RankedPolicy:
    policy: Policy
    score: float


def tokenize(text: str) -> list[str]:
    return [token.lower() for token in TOKEN_RE.findall(text) if len(token) > 2 and token.lower() not in STOP]


def rank_policies(
    query: str,
    policies: list[Policy],
    limit: int = 3,
    category: str | None = None,
    language: str | None = None,
) -> list[Citation]:
    query_tokens = tokenize(query)
    if not query_tokens:
        return []
    query_set = set(query_tokens)
    ranked: list[RankedPolicy] = []
    for policy in policies:
        tokens = tokenize(f"{policy.title} {policy.category} {policy.content}")
        if not tokens:
            continue
        counts = {token: tokens.count(token) for token in query_set}
        overlap = sum(math.log1p(count) for count in counts.values() if count)
        category_bonus = 3.0 if category and policy.category == category else 0.0
        language_bonus = 1.0 if language and policy.language == language else 0.0
        score = overlap + category_bonus + language_bonus
        if score > 0:
            ranked.append(RankedPolicy(policy, round(score, 3)))
    ranked.sort(key=lambda item: item.score, reverse=True)
    return [
        Citation(
            policy_slug=item.policy.slug,
            policy_title=item.policy.title,
            excerpt=item.policy.content[:220].strip(),
            score=item.score,
        )
        for item in ranked[:limit]
    ]
