from __future__ import annotations

import math
import re
from collections.abc import Iterable
from datetime import datetime, timezone

STOPWORDS = {
    "a",
    "an",
    "and",
    "application",
    "are",
    "as",
    "at",
    "based",
    "be",
    "best",
    "build",
    "business",
    "by",
    "can",
    "canada",
    "client",
    "clients",
    "company",
    "content",
    "cross",
    "customer",
    "customers",
    "data",
    "day",
    "days",
    "division",
    "drive",
    "driven",
    "email",
    "engineering",
    "experience",
    "for",
    "from",
    "get",
    "had",
    "how",
    "improved",
    "in",
    "into",
    "is",
    "it",
    "job",
    "led",
    "llm",
    "management",
    "marketing",
    "month",
    "months",
    "of",
    "on",
    "ontario",
    "or",
    "per",
    "product",
    "projects",
    "python",
    "role",
    "roles",
    "service",
    "services",
    "small",
    "start",
    "team",
    "teams",
    "template",
    "the",
    "that",
    "through",
    "time",
    "toronto",
    "to",
    "using",
    "via",
    "worked",
    "year",
    "years",
    "with",
}

QUESTION_PREFIXES = ("how", "what", "why", "when", "where", "can", "should", "which")
INTENT_MARKERS = ("template", "software", "tool", "tools", "consultant", "service", "services", "ideas", "reddit")
BUSINESS_SIGNAL_TOKENS = {
    "analysis",
    "analytics",
    "api",
    "apis",
    "automation",
    "dashboard",
    "data",
    "engineering",
    "integration",
    "integrations",
    "llm",
    "marketing",
    "operations",
    "optimization",
    "pipeline",
    "pipelines",
    "postgresql",
    "python",
    "rag",
    "report",
    "reporting",
    "research",
    "seo",
    "sql",
    "strategy",
    "terraform",
    "visualization",
    "workflow",
    "workflows",
}
DISCOVERY_SIGNAL_TOKENS = {
    "analytics",
    "automation",
    "dashboard",
    "integration",
    "integrations",
    "marketing",
    "operations",
    "optimization",
    "report",
    "reporting",
    "research",
    "seo",
    "strategy",
    "visualization",
    "workflow",
    "workflows",
}


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def slugify(value: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9]+", "-", value.strip().lower()).strip("-")
    return cleaned or "run"


def tokenize(text: str) -> list[str]:
    return re.findall(r"[a-zA-Z0-9][a-zA-Z0-9+#/&-]{1,}", text.lower())


def content_tokens(text: str) -> list[str]:
    return [token for token in tokenize(text) if token not in STOPWORDS and len(token) > 2]


def dedupe_preserve_order(values: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    output: list[str] = []
    for value in values:
        key = value.strip().lower()
        if not key or key in seen:
            continue
        seen.add(key)
        output.append(value.strip())
    return output


def chunks(values: list[str], size: int) -> list[list[str]]:
    return [values[index : index + size] for index in range(0, len(values), size)]


def clamp01(value: float | None) -> float:
    if value is None or math.isnan(value):
        return 0.0
    return max(0.0, min(1.0, float(value)))


def safe_mean(values: Iterable[float]) -> float:
    data = list(values)
    return sum(data) / len(data) if data else 0.0


def minmax_scale(mapping: dict[str, float]) -> dict[str, float]:
    if not mapping:
        return {}
    values = list(mapping.values())
    low = min(values)
    high = max(values)
    if math.isclose(low, high):
        return {key: 1.0 if high > 0 else 0.0 for key in mapping}
    return {key: (value - low) / (high - low) for key, value in mapping.items()}


def is_question_like(text: str) -> bool:
    lowered = text.lower().strip()
    return (
        lowered.startswith(QUESTION_PREFIXES)
        or " how " in f" {lowered} "
        or any(marker in lowered for marker in INTENT_MARKERS)
    )


def shared_token_score(left: str, right: str) -> float:
    a = set(content_tokens(left))
    b = set(content_tokens(right))
    if not a or not b:
        return 0.0
    overlap = len(a & b)
    union = len(a | b)
    return overlap / union if union else 0.0


def token_overlap_score(left: str, right: str) -> float:
    left_tokens = set(content_tokens(left))
    right_tokens = set(content_tokens(right))
    if not left_tokens or not right_tokens:
        return 0.0
    overlap = len(left_tokens & right_tokens)
    return overlap / max(1, len(right_tokens))


def informative_phrase(phrase: str, min_tokens: int = 2, max_tokens: int = 4) -> bool:
    tokens = content_tokens(phrase)
    if len(tokens) < min_tokens or len(tokens) > max_tokens:
        return False
    if any(token.isdigit() for token in tokens):
        return False
    banned = {"toronto", "ontario", "canada", "month", "year", "time", "application"}
    if any(token in banned for token in tokens):
        return False
    if not any(token in BUSINESS_SIGNAL_TOKENS for token in tokens):
        return False
    return True


def normalize_search_term(term: str) -> str:
    term = re.sub(r"^(how to|best)\s+", "", term.strip().lower())
    term = re.sub(r"\s+", " ", term)
    return term
