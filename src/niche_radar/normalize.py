from __future__ import annotations

from .models import ProviderResult, TermRecord
from .utils import is_question_like


def combine_provider_signals(records: list[TermRecord], provider_results: list[ProviderResult]) -> dict[str, dict]:
    combined: dict[str, dict] = {
        record.term: {
            "term": record.term,
            "generation": record.generation,
            "lineage_root": record.lineage_root,
            "parent_term": record.parent_term,
            "source": record.source,
            "hits": [],
            "providers": set(),
            "degraded_reasons": [],
        }
        for record in records
    }

    for provider_result in provider_results:
        if provider_result.status in {"degraded", "unavailable"} and provider_result.reason:
            for term in combined.values():
                term["degraded_reasons"].append(f"{provider_result.provider}: {provider_result.reason}")

        for term, metrics in provider_result.metrics.items():
            if term not in combined:
                continue
            combined[term]["providers"].add(provider_result.provider)
            combined[term].update(metrics)

        for term, hits in provider_result.hits.items():
            if term not in combined:
                continue
            combined[term]["providers"].add(provider_result.provider)
            for hit in hits:
                combined[term]["hits"].append({"provider": provider_result.provider, **hit})

    for term_data in combined.values():
        hits = term_data["hits"]
        unique_texts = {hit.get("text", "").strip().lower() for hit in hits if hit.get("text")}
        question_hits = [hit for hit in hits if hit.get("question_like") or is_question_like(hit.get("text", ""))]
        term_data["adjacency_count_raw"] = float(len(unique_texts))
        term_data["question_density_raw"] = (len(question_hits) / len(hits)) if hits else 0.0
        term_data["surface_spread_raw"] = float(len(term_data["providers"]))
        term_data["providers"] = sorted(term_data["providers"])

    return combined

