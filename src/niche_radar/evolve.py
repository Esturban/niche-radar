from __future__ import annotations

import os
from collections import defaultdict

from .models import TermRecord
from .signal_quality import classify_signal_text
from .utils import DISCOVERY_SIGNAL_TOKENS, content_tokens, dedupe_preserve_order, normalize_search_term

_DEFAULT_OPENAI_MODEL = "gpt-5.4-nano"
_DEFAULT_REASONING_EFFORT = "xhigh"
_ALLOWED_REASONING_EFFORTS = {"none", "minimal", "low", "medium", "high", "xhigh"}


def expand_terms(
    records: list[TermRecord],
    topic: str,
    profile: dict,
    generation: int,
) -> list[TermRecord]:
    expanded: list[TermRecord] = []
    keyword_pool = [keyword for keyword in profile.get("keywords", []) if keyword in DISCOVERY_SIGNAL_TOKENS][:6]

    for record in records:
        base = normalize_search_term(record.term)
        base_tokens = set(content_tokens(base))
        heuristics = [f"how to {base}", f"{base} software", f"{base} template", f"{base} consultant"]
        if "workflow" not in base_tokens:
            heuristics.append(f"{base} workflow")
        if "automation" not in base_tokens:
            heuristics.append(f"{base} automation")
        heuristics.extend(
            f"{base} {keyword}" for keyword in keyword_pool[:2] if keyword not in base_tokens
        )

        llm_terms = _maybe_llm_expand(base=base, topic=topic, keyword_pool=keyword_pool)
        for term in dedupe_preserve_order(heuristics + llm_terms)[:8]:
            expanded.append(
                TermRecord(
                    term=term,
                    generation=generation,
                    source="llm" if term in llm_terms else "heuristic",
                    lineage_root=record.lineage_root,
                    parent_term=record.term,
                    signal_class=classify_signal_text(term),
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
        model = _resolve_openai_model()
        request: dict[str, object] = {
            "model": model,
            "input": prompt,
            "max_output_tokens": 200,
        }
        reasoning_effort = _resolve_reasoning_effort()
        if _supports_reasoning(model):
            request["reasoning"] = {"effort": reasoning_effort}

        client = OpenAI(api_key=api_key)
        response = client.responses.create(**request)
    except Exception:
        return []

    text = getattr(response, "output_text", "") or ""
    return [line.strip("- ").strip() for line in text.splitlines() if line.strip()]


def _resolve_openai_model() -> str:
    model = os.getenv("NICHE_RADAR_OPENAI_MODEL", _DEFAULT_OPENAI_MODEL).strip()
    return model or _DEFAULT_OPENAI_MODEL


def _resolve_reasoning_effort() -> str:
    value = os.getenv("NICHE_RADAR_OPENAI_REASONING", _DEFAULT_REASONING_EFFORT).strip().lower()
    if value in _ALLOWED_REASONING_EFFORTS:
        return value
    return _DEFAULT_REASONING_EFFORT


def _supports_reasoning(model: str) -> bool:
    normalized = model.strip().lower()
    return normalized.startswith(("gpt-5", "o"))


def lineage_generations(records: list[TermRecord]) -> dict[str, set[int]]:
    generations: dict[str, set[int]] = defaultdict(set)
    for record in records:
        generations[record.lineage_root].add(record.generation)
    return generations
