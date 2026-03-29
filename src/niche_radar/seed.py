from __future__ import annotations

from .utils import content_tokens, dedupe_preserve_order, informative_phrase


def generate_seed_terms(profile: dict, topic: str, limit: int = 12) -> list[str]:
    phrases = profile.get("phrases", [])
    keywords = profile.get("keywords", [])
    themes = profile.get("themes", [])
    topic_tokens = set(content_tokens(topic))

    candidates = [topic]

    for phrase in phrases[:8]:
        if not informative_phrase(phrase):
            continue
        candidates.extend(
            [
                f"{topic} {phrase}",
                f"{phrase} for small business",
                f"{phrase} workflow",
            ]
        )
        if topic_tokens & set(content_tokens(phrase)):
            candidates.append(phrase)

    for keyword in keywords[:8]:
        candidates.extend(
            [
                f"{topic} {keyword} workflow",
                f"{topic} {keyword} automation",
            ]
        )

    for theme in themes[:6]:
        if informative_phrase(theme):
            candidates.append(f"{theme} small business")

    return dedupe_preserve_order(candidates)[:limit]
