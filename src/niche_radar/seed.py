from __future__ import annotations

from .utils import DISCOVERY_SIGNAL_TOKENS, content_tokens, dedupe_preserve_order, informative_phrase


def generate_seed_terms(profile: dict, topic: str, limit: int = 18) -> list[str]:
    phrases = profile.get("phrases", [])
    keywords = profile.get("keywords", [])
    topic_lower = topic.lower()
    small_business_mode = "small business" in topic_lower or "solopreneur" in topic_lower
    operations_mode = "operations" in topic_lower

    candidates: list[str] = []
    if small_business_mode:
        candidates.extend(
            [
                "small business automation",
                "small business dashboard",
                "small business analytics",
                "small business reporting",
            ]
        )
    candidates.extend(
        [
            "business process automation",
            "workflow automation",
            "reporting automation",
            "analytics dashboards",
            "dashboard workflows",
        ]
    )

    for keyword in keywords[:8]:
        if keyword not in DISCOVERY_SIGNAL_TOKENS:
            continue
        if keyword != "workflow":
            candidates.append(f"{keyword} workflow")
        if keyword != "automation":
            candidates.append(f"{keyword} automation")
        if small_business_mode:
            candidates.extend([f"small business {keyword}", f"{keyword} for small business"])

    for phrase in phrases[:6]:
        if not informative_phrase(phrase):
            continue
        if not any(token in DISCOVERY_SIGNAL_TOKENS for token in content_tokens(phrase)):
            continue
        compact_phrase = phrase.replace("development", "workflows").strip()
        candidates.append(compact_phrase)
        if small_business_mode:
            candidates.append(f"{compact_phrase} for small business")
        if operations_mode and "operations" not in compact_phrase:
            candidates.append(f"operations {compact_phrase}")

    return dedupe_preserve_order(candidates)[:limit]
