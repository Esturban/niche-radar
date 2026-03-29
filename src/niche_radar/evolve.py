from __future__ import annotations

import os
from collections import defaultdict

from .models import TermRecord
from .utils import dedupe_preserve_order


def expand_terms(
    records: list[TermRecord],
    topic: str,
    profile: dict,
    generation: int,
) -> list[TermRecord]:
    expanded: list[TermRecord] = []
    keyword_pool = profile.get("keywords", [])[:8]
    phrase_pool = profile.get("phrases", [])[:6]

    for record in records:
        base = record.term
        heuristics = [
            f"how to {base}",
            f"best {base} for small business",
            f"{base} automation",
            f"{base} template",
            f"{base} consultant",
            f"{base} service",
            f"{topic} {base}",
        ]
        heuristics.extend(f"{base} {keyword}" for keyword in keyword_pool[:3])
        heuristics.extend(f"{base} {phrase}" for phrase in phrase_pool[:2])

        llm_terms = _maybe_llm_expand(base=base, topic=topic, keyword_pool=keyword_pool)
        for term in dedupe_preserve_order(heuristics + llm_terms)[:8]:
            expanded.append(
                TermRecord(
                    term=term,
                    generation=generation,
                    source="llm" if term in llm_terms else "heuristic",
                    lineage_root=record.lineage_root,
                    parent_term=record.term,
                )
            )

    return _dedupe_term_records(expanded)


def _dedupe_term_records(records: list[TermRecord]) -> list[TermRecord]:
    deduped: dict[str, TermRecord] = {}
    for record in records:
        key = record.term.strip().lower()
        if key not in deduped:
            deduped[key] = record
    return list(deduped.values())


def _maybe_llm_expand(base: str, topic: str, keyword_pool: list[str]) -> list[str]:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return []

    try:
        from openai import OpenAI
    except ImportError:
        return []

    prompt = (
        "Generate 5 adjacent niche-search phrases, one per line. "
        "No numbering, no explanation. "
        f"Base term: {base}. Topic: {topic}. Keywords: {', '.join(keyword_pool[:5])}."
    )

    try:
        client = OpenAI(api_key=api_key)
        response = client.responses.create(
            model=os.getenv("NICHE_RADAR_OPENAI_MODEL", "gpt-4.1-mini"),
            input=prompt,
            max_output_tokens=200,
        )
    except Exception:
        return []

    text = getattr(response, "output_text", "") or ""
    return [line.strip("- ").strip() for line in text.splitlines() if line.strip()]


def lineage_generations(records: list[TermRecord]) -> dict[str, set[int]]:
    generations: dict[str, set[int]] = defaultdict(set)
    for record in records:
        generations[record.lineage_root].add(record.generation)
    return generations

