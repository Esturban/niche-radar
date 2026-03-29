from __future__ import annotations

from dataclasses import asdict
from pathlib import Path

from .cluster import build_question_graph, cluster_terms
from .collect import (
    collect_autosuggest,
    collect_keyword_planner,
    collect_search_console,
    collect_trends,
    collect_youtube,
)
from .evolve import expand_terms
from .ingest import load_resume
from .models import ProviderResult, RunConfig, TermRecord
from .normalize import combine_provider_signals
from .profile import extract_profile
from .rank import score_clusters
from .report import append_run_index, write_outputs
from .seed import generate_seed_terms
from .utils import content_tokens, now_iso, shared_token_score, slugify


def discover(config: RunConfig) -> dict:
    resume_text = load_resume(config.resume_path)
    profile = extract_profile(resume_text)
    seeds = generate_seed_terms(profile=profile, topic=config.topic)

    generation_zero = [
        TermRecord(term=term, generation=0, source="seed", lineage_root=term)
        for term in seeds
    ]
    generation_one = expand_terms(records=generation_zero, topic=config.topic, profile=profile, generation=1)

    preliminary_records = _unique_records(generation_zero + generation_one)
    preliminary_provider_results = _collect_provider_round(
        config=config,
        terms=_provider_query_terms(records=preliminary_records, profile=profile, topic=config.topic),
    )
    preliminary_terms = combine_provider_signals(preliminary_records, preliminary_provider_results)

    survivors = _select_survivors(preliminary_terms, limit=max(4, min(12, config.max_clusters)))
    generation_two = expand_terms(records=survivors, topic=config.topic, profile=profile, generation=2)
    final_records = _unique_records(preliminary_records + generation_two)

    provider_results = _collect_provider_round(
        config=config,
        terms=_provider_query_terms(records=final_records, profile=profile, topic=config.topic),
    )
    all_terms_map = combine_provider_signals(final_records, provider_results)
    all_terms = list(all_terms_map.values())

    active_provider_count = sum(1 for result in provider_results if result.status in {"ok", "degraded"} and (result.metrics or result.hits))
    if active_provider_count == 0:
        return _write_insufficient_signal(config=config, profile=profile, seeds=seeds, reasons=[result.reason for result in provider_results if result.reason])

    clusters = cluster_terms(all_terms_map)
    ranked_clusters, _ = score_clusters(clusters=clusters, profile=profile, total_generations=config.generations)
    question_graph = build_question_graph(ranked_clusters)

    outdir = config.outdir
    confidence_floor = min((cluster["confidence"] for cluster in ranked_clusters), default=0.0)
    run_meta = {
        "generated_at": now_iso(),
        "resume_path": str(config.resume_path),
        "topic": config.topic,
        "profile_summary": {
            "keywords": profile.get("keywords", [])[:10],
            "phrases": profile.get("phrases", [])[:8],
        },
        "provider_statuses": [asdict(result) for result in provider_results],
        "confidence_floor": round(confidence_floor, 4),
        "seed_terms": seeds,
    }

    write_outputs(
        outdir=outdir,
        clusters=ranked_clusters,
        all_terms=all_terms,
        question_graph=question_graph,
        provider_results=[asdict(result) for result in provider_results],
        run_meta=run_meta,
        max_clusters=config.max_clusters,
    )
    append_run_index(
        outdir.parent,
        {
            "topic": config.topic,
            "slug": slugify(config.topic),
            "outdir": str(outdir),
            "cluster_count": len(ranked_clusters[: config.max_clusters]),
            "confidence_floor": round(confidence_floor, 4),
        },
    )
    return {"outdir": str(outdir), "cluster_count": len(ranked_clusters[: config.max_clusters]), "insufficient_signal": False}


def _unique_records(records: list[TermRecord]) -> list[TermRecord]:
    deduped: dict[str, TermRecord] = {}
    for record in records:
        key = record.term.strip().lower()
        if key not in deduped:
            deduped[key] = record
    return list(deduped.values())


def _collect_provider_round(config: RunConfig, terms: list[str]) -> list[ProviderResult]:
    results = [
        collect_trends(terms=terms, topic=config.topic, geo=config.geo),
        collect_autosuggest(terms=terms),
        collect_youtube(terms=terms),
    ]
    if config.with_search_console:
        results.append(collect_search_console(terms=terms))
    else:
        results.append(ProviderResult(provider="search_console", status="unavailable", reason="disabled"))
    if config.with_keyword_planner:
        results.append(collect_keyword_planner(terms=terms))
    else:
        results.append(ProviderResult(provider="keyword_planner", status="unavailable", reason="disabled"))
    return results


def _provider_query_terms(records: list[TermRecord], profile: dict, topic: str, limit: int = 18) -> list[str]:
    profile_signals = set(profile.get("keywords", []) + profile.get("phrases", []) + profile.get("themes", []))
    topic_tokens = set(content_tokens(topic))

    def score(record: TermRecord) -> tuple[float, int, int]:
        term_tokens = set(content_tokens(record.term))
        overlap = len(term_tokens & profile_signals)
        topic_overlap = len(term_tokens & topic_tokens)
        lexical = shared_token_score(record.term, topic)
        anchored = 1 if overlap > 0 else 0
        return (anchored + lexical + (0.1 * topic_overlap), -record.generation, -len(term_tokens))

    filtered = []
    for record in records:
        term_tokens = set(content_tokens(record.term))
        if not term_tokens:
            continue
        if term_tokens & profile_signals or term_tokens & topic_tokens:
            filtered.append(record)

    ranked = sorted(filtered, key=score, reverse=True)
    seen: set[str] = set()
    output: list[str] = []
    for record in ranked:
        key = record.term.lower().strip()
        if key in seen:
            continue
        seen.add(key)
        output.append(record.term)
        if len(output) >= limit:
            break
    return output


def _select_survivors(term_states: dict[str, dict], limit: int) -> list[TermRecord]:
    scored = sorted(
        term_states.values(),
        key=lambda item: (
            item.get("trend_strength_raw", 0.0),
            item.get("adjacency_count_raw", 0.0),
            item.get("surface_spread_raw", 0.0),
        ),
        reverse=True,
    )
    return [
        TermRecord(
            term=item["term"],
            generation=item["generation"],
            source=item["source"],
            lineage_root=item["lineage_root"],
            parent_term=item["parent_term"],
        )
        for item in scored[:limit]
    ]


def _write_insufficient_signal(config: RunConfig, profile: dict, seeds: list[str], reasons: list[str]) -> dict:
    import json

    outdir = config.outdir
    outdir.mkdir(parents=True, exist_ok=True)
    report = "\n".join(
        [
            "# niche-radar report",
            "",
            "## Insufficient signal",
            "- No free providers returned enough live signal to rank niche territories honestly.",
            "- This run did not force a winner.",
            "",
            "## Topic",
            f"- `{config.topic}`",
            "",
            "## Seed terms attempted",
            *[f"- {seed}" for seed in seeds],
            "",
            "## Why the run degraded",
            *[f"- {reason}" for reason in reasons if reason],
            "",
            "## Next step",
            "- Enable a free provider such as pytrends, Bing Autosuggest, or YouTube Data API and rerun.",
        ]
    )
    (outdir / "report.md").write_text(report + "\n", encoding="utf-8")
    (outdir / "clusters.json").write_text("[]\n", encoding="utf-8")
    (outdir / "question_graph.json").write_text('{"nodes":[],"edges":[]}\n', encoding="utf-8")
    (outdir / "provider_hits.json").write_text("[]\n", encoding="utf-8")
    (outdir / "run_meta.json").write_text(
        json.dumps(
            {
                "generated_at": now_iso(),
                "resume_path": str(config.resume_path),
                "topic": config.topic,
                "profile_summary": profile,
                "insufficient_signal": True,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    append_run_index(
        outdir.parent,
        {
            "topic": config.topic,
            "slug": slugify(config.topic),
            "outdir": str(outdir),
            "cluster_count": 0,
            "confidence_floor": 0.0,
            "insufficient_signal": True,
        },
    )
    return {"outdir": str(outdir), "cluster_count": 0, "insufficient_signal": True}
