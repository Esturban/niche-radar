from __future__ import annotations

from .utils import DISCOVERY_SIGNAL_TOKENS, content_tokens, dedupe_preserve_order, informative_phrase, normalize_search_term

DEFAULT_GENERIC_SEEDS = [
    "business process automation",
    "workflow automation",
    "reporting automation",
    "analytics dashboards",
    "dashboard workflows",
]
DEFAULT_TOPIC_SIGNALS = ["analytics", "automation", "dashboard", "reporting", "operations", "workflow"]


def generate_seed_terms(profile: dict, topic: str, limit: int = 18) -> list[str]:
    seeds, _ = build_seed_plan(profile=profile, topic=topic, limit=limit)
    return seeds


def build_seed_plan(profile: dict, topic: str, limit: int = 18) -> tuple[list[str], dict]:
    phrases = profile.get("phrases", [])
    keywords = profile.get("keywords", [])
    topic = normalize_search_term(topic)
    topic_lower = topic.lower()
    topic_tokens = content_tokens(topic)
    small_business_mode = "small business" in topic_lower or "solopreneur" in topic_lower
    operations_mode = "operations" in topic_lower

    candidates: list[dict[str, str]] = []
    if topic_tokens:
        candidates.extend(_topic_seed_candidates(topic=topic, topic_tokens=topic_tokens, keywords=keywords, phrases=phrases))
    else:
        candidates.extend(_generic_seed_candidates(keywords=keywords, phrases=phrases, small_business_mode=small_business_mode, operations_mode=operations_mode))

    accepted: list[dict[str, str]] = []
    rejected: list[dict[str, str]] = []
    seen: set[str] = set()
    for candidate in candidates:
        term = normalize_search_term(candidate["term"])
        reason = _seed_rejection_reason(term=term, topic_tokens=topic_tokens)
        entry = {"term": term, "source": candidate["source"]}
        if reason:
            rejected.append({**entry, "reason": reason})
            continue
        if term in seen:
            continue
        seen.add(term)
        accepted.append(entry)

    seeds = [entry["term"] for entry in accepted[:limit]]
    summary = {
        "accepted": accepted[:limit],
        "rejected": rejected[:limit],
    }
    return seeds, summary


def _topic_seed_candidates(topic: str, topic_tokens: list[str], keywords: list[str], phrases: list[str]) -> list[dict[str, str]]:
    profile_signals = [keyword for keyword in keywords if keyword in DISCOVERY_SIGNAL_TOKENS][:6]
    topic_signals = [token for token in topic_tokens if token in DISCOVERY_SIGNAL_TOKENS]
    signals = dedupe_preserve_order(profile_signals + topic_signals + DEFAULT_TOPIC_SIGNALS)

    anchors = [topic]
    anchors.extend(token for token in topic_tokens if token not in DISCOVERY_SIGNAL_TOKENS)

    candidates = [{"term": topic, "source": "focus"}]
    for anchor in dedupe_preserve_order(anchors):
        for signal in signals[:6]:
            if signal in content_tokens(anchor):
                continue
            candidates.append({"term": f"{anchor} {signal}", "source": "focus"})

    for phrase in phrases[:6]:
        if not informative_phrase(phrase):
            continue
        compact_phrase = phrase.replace("development", "workflows").strip()
        phrase_tokens = content_tokens(compact_phrase)
        if not phrase_tokens:
            continue
        if set(phrase_tokens) & set(topic_tokens):
            candidates.append({"term": compact_phrase, "source": "profile_phrase"})
            continue
        signal_tokens = [token for token in phrase_tokens if token in DISCOVERY_SIGNAL_TOKENS]
        if not signal_tokens:
            continue
        candidates.append({"term": f"{topic} {signal_tokens[0]}", "source": "profile_phrase"})

    return candidates


def _generic_seed_candidates(
    *,
    keywords: list[str],
    phrases: list[str],
    small_business_mode: bool,
    operations_mode: bool,
) -> list[dict[str, str]]:
    candidates: list[dict[str, str]] = []
    if small_business_mode:
        for term in [
            "small business automation",
            "small business dashboard",
            "small business analytics",
            "small business reporting",
        ]:
            candidates.append({"term": term, "source": "generic"})
    for term in DEFAULT_GENERIC_SEEDS:
        candidates.append({"term": term, "source": "generic"})

    for keyword in keywords[:8]:
        if keyword not in DISCOVERY_SIGNAL_TOKENS:
            continue
        if keyword != "workflow":
            candidates.append({"term": f"{keyword} workflow", "source": "profile_keyword"})
        if keyword != "automation":
            candidates.append({"term": f"{keyword} automation", "source": "profile_keyword"})
        if small_business_mode:
            candidates.append({"term": f"small business {keyword}", "source": "profile_keyword"})
            candidates.append({"term": f"{keyword} for small business", "source": "profile_keyword"})

    for phrase in phrases[:6]:
        if not informative_phrase(phrase):
            continue
        if not any(token in DISCOVERY_SIGNAL_TOKENS for token in content_tokens(phrase)):
            continue
        compact_phrase = phrase.replace("development", "workflows").strip()
        candidates.append({"term": compact_phrase, "source": "profile_phrase"})
        if small_business_mode:
            candidates.append({"term": f"{compact_phrase} for small business", "source": "profile_phrase"})
        if operations_mode and "operations" not in compact_phrase:
            candidates.append({"term": f"operations {compact_phrase}", "source": "profile_phrase"})
    return candidates


def _seed_rejection_reason(*, term: str, topic_tokens: list[str]) -> str | None:
    if not term:
        return "empty term"
    tokens = content_tokens(term)
    if not tokens:
        return "no usable tokens"
    if topic_tokens and not (set(tokens) & set(topic_tokens)):
        return "not focus-anchored"
    return None
