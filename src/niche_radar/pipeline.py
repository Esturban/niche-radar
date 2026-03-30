from __future__ import annotations

import re
from dataclasses import asdict
from pathlib import Path

from .cluster import build_question_graph, cluster_terms
from .collect import (
    collect_autosuggest,
    collect_evidence_search,
    collect_keyword_planner,
    collect_search_console,
    collect_trends,
    collect_youtube,
    flatten_evidence,
)
from .evolve import expand_terms
from .ingest import load_profile
from .models import ProviderResult, RunConfig, TermRecord
from .narrow import attach_micro_wedges
from .normalize import combine_provider_signals
from .profile import extract_profile
from .rank import score_clusters
from .research_graph import apply_research_graph
from .report import append_run_index, write_outputs
from .seed import generate_seed_terms
from .utils import DISCOVERY_SIGNAL_TOKENS, content_tokens, dedupe_preserve_order, normalize_search_term, now_iso, shared_token_score, slugify


def discover(config: RunConfig) -> dict:
    profile_source = load_profile(resume_path=config.resume_path, site_url=config.site_url)
    profile = extract_profile(profile_source.text)
    focus = config.focus or ""
    seeds = generate_seed_terms(profile=profile, topic=focus)

    generation_zero = [
        TermRecord(term=term, generation=0, source="seed", lineage_root=term)
        for term in seeds
    ]
    generation_one = expand_terms(records=generation_zero, topic=focus, profile=profile, generation=1)

    preliminary_records = _unique_records(generation_zero + generation_one)
    preliminary_provider_results = _collect_provider_round(
        config=config,
        terms=_provider_query_terms(records=preliminary_records, profile=profile, topic=focus),
    )
    preliminary_terms = combine_provider_signals(preliminary_records, preliminary_provider_results)

    survivors = _select_survivors(preliminary_terms, limit=max(4, min(12, config.top_niches * 2)))
    generation_two = expand_terms(records=survivors, topic=focus, profile=profile, generation=2)
    final_records = _unique_records(preliminary_records + generation_two)

    provider_results = _collect_provider_round(
        config=config,
        terms=_provider_query_terms(records=final_records, profile=profile, topic=focus),
    )
    all_terms_map = combine_provider_signals(final_records, provider_results)
    all_terms = list(all_terms_map.values())

    active_provider_count = sum(1 for result in provider_results if result.status in {"ok", "degraded"} and (result.metrics or result.hits))
    if active_provider_count == 0:
        return _write_insufficient_signal(config=config, profile=profile, profile_source=profile_source, seeds=seeds, reasons=[result.reason for result in provider_results if result.reason])

    clusters = cluster_terms(all_terms_map)
    initial_ranked_clusters, _ = score_clusters(clusters=clusters, profile=profile, total_generations=config.generations, topic=focus)
    evidence_candidates = initial_ranked_clusters[: max(config.top_niches * 2, config.top_niches)]
    evidence_by_cluster = collect_evidence_search(clusters=evidence_candidates, focus=focus, evidence_pages=config.evidence_pages)
    narrowed_clusters = attach_micro_wedges(clusters=clusters, evidence_by_cluster=evidence_by_cluster)
    ranked_clusters, _ = score_clusters(
        clusters=narrowed_clusters,
        profile=profile,
        total_generations=config.generations,
        topic=focus,
        evidence_by_cluster=evidence_by_cluster,
    )
    ranked_clusters, research_trace = apply_research_graph(
        ranked_clusters=ranked_clusters,
        focus=focus,
        research_depth=config.research_depth,
        research_top_k=config.research_top_k,
        evidence_pages=config.evidence_pages,
        llm_provider=config.llm_provider,
    )
    question_graph = build_question_graph(ranked_clusters)
    evidence = flatten_evidence(evidence_by_cluster)
    used_evidence = _collect_used_evidence(ranked_clusters[: config.top_niches])

    outdir = config.outdir
    confidence_floor = min((cluster["confidence"] for cluster in ranked_clusters), default=0.0)
    recommended_bet_count = sum(1 for cluster in ranked_clusters if cluster.get("recommended_bet"))
    run_meta = {
        "generated_at": now_iso(),
        "resume_path": str(config.resume_path) if config.resume_path else None,
        "site_url": config.site_url,
        "focus": focus,
        "profile_sources": profile_source.metadata.get("sources", []),
        "profile_summary": {
            "keywords": profile.get("keywords", [])[:10],
            "phrases": profile.get("phrases", [])[:8],
        },
        "provider_statuses": [asdict(result) for result in provider_results],
        "evidence_summary": {
            "clusters_evaluated": len(evidence_candidates),
            "citations_collected": len(evidence),
        },
        "wedge_summary": {
            "clusters_with_wedges": sum(1 for cluster in ranked_clusters if cluster.get("micro_wedges")),
            "recommended_bet_count": recommended_bet_count,
            "near_miss_count": sum(1 for cluster in ranked_clusters if not cluster.get("recommended_bet")),
            "specificity_outcome": "recommended_bets_found" if recommended_bet_count else "not_specific_enough",
        },
        "research_summary": {
            "depth": config.research_depth,
            "shortlisted": min(config.research_top_k, len(ranked_clusters)),
            "provider": config.llm_provider,
        },
        "confidence_floor": round(confidence_floor, 4),
        "seed_terms": seeds,
    }

    write_outputs(
        outdir=outdir,
        clusters=ranked_clusters,
        all_terms=all_terms,
        question_graph=question_graph,
        evidence=evidence,
        used_evidence=used_evidence,
        provider_results=[asdict(result) for result in provider_results],
        run_meta=run_meta,
        top_niches=config.top_niches,
        research_trace=research_trace,
        persist_trace=config.persist_trace,
    )
    append_run_index(
        outdir.parent,
        {
            "focus": focus,
            "slug": slugify(focus or config.site_url or (config.resume_path.stem if config.resume_path else "profile-driven")),
            "outdir": str(outdir),
            "cluster_count": len(ranked_clusters[: config.top_niches]),
            "confidence_floor": round(confidence_floor, 4),
        },
    )
    return {"outdir": str(outdir), "cluster_count": len(ranked_clusters[: config.top_niches]), "insufficient_signal": False}


def _unique_records(records: list[TermRecord]) -> list[TermRecord]:
    deduped: dict[str, TermRecord] = {}
    for record in records:
        key = record.term.strip().lower()
        if key not in deduped:
            deduped[key] = record
    return list(deduped.values())


def _collect_provider_round(config: RunConfig, terms: list[str]) -> list[ProviderResult]:
    results = [
        collect_trends(terms=terms, topic=config.focus, geo=config.geo),
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
    profile_signals = {
        token
        for value in profile.get("keywords", []) + profile.get("phrases", []) + profile.get("themes", [])
        for token in content_tokens(value)
    }
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
        for variant in _provider_variants(record.term, topic):
            key = variant.lower().strip()
            if key in seen:
                continue
            seen.add(key)
            output.append(variant)
            if len(output) >= limit:
                return output
    return output


def _provider_variants(term: str, topic: str) -> list[str]:
    normalized = normalize_search_term(term)
    tokens = content_tokens(normalized)
    signal_tokens = [token for token in tokens if token in DISCOVERY_SIGNAL_TOKENS]
    variants = [normalized]

    if "small business" in topic.lower():
        for token in signal_tokens[:2]:
            variants.extend(
                [
                    f"small business {token}",
                    f"{token} for small business",
                ]
            )
            if "operations" in topic.lower():
                variants.append(f"small business operations {token}")

    if "operations" in topic.lower() and "automation" in signal_tokens:
        variants.append("business process automation")

    compressed = _compress_long_term(normalized, signal_tokens)
    if compressed:
        variants.append(compressed)

    cleaned = []
    for variant in dedupe_preserve_order(variants):
        variant = re.sub(r"\s+", " ", variant).strip()
        if not variant:
            continue
        token_count = len(content_tokens(variant))
        if token_count == 0 or token_count > 4:
            continue
        if "small business" not in variant and token_count < 2:
            continue
        cleaned.append(variant)
    return cleaned


def _compress_long_term(term: str, signal_tokens: list[str]) -> str | None:
    if not signal_tokens:
        return None
    primary = signal_tokens[0]
    if "small business" in term:
        return f"small business {primary}"
    return f"{primary} workflow"


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


def _write_insufficient_signal(config: RunConfig, profile: dict, profile_source, seeds: list[str], reasons: list[str]) -> dict:
    import json

    outdir = config.outdir
    focus = config.focus or "profile-driven"
    outdir.mkdir(parents=True, exist_ok=True)
    report = "\n".join(
        [
            "# niche-radar report",
            "",
            "## Insufficient signal",
            "- No external providers returned enough live signal to rank niches honestly.",
            "- This run did not force a winner.",
            "",
            "## Focus",
            f"- `{focus}`",
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
    (outdir / "used_evidence.json").write_text("[]\n", encoding="utf-8")
    (outdir / "run_meta.json").write_text(
        json.dumps(
            {
                "generated_at": now_iso(),
                "resume_path": str(config.resume_path) if config.resume_path else None,
                "site_url": config.site_url,
                "focus": config.focus,
                "profile_sources": profile_source.metadata.get("sources", []),
                "profile_summary": profile,
                "insufficient_signal": True,
                "research_summary": {
                    "depth": config.research_depth,
                    "shortlisted": 0,
                    "provider": config.llm_provider,
                },
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    if config.persist_trace:
        (outdir / "evidence.json").write_text("[]\n", encoding="utf-8")
        (outdir / "question_graph.json").write_text('{"nodes":[],"edges":[]}\n', encoding="utf-8")
        (outdir / "provider_hits.json").write_text("[]\n", encoding="utf-8")
        (outdir / "research_trace.json").write_text('{"depth":"' + config.research_depth + '","entries":[]}\n', encoding="utf-8")
    append_run_index(
        outdir.parent,
        {
            "focus": config.focus,
            "slug": slugify(config.focus or config.site_url or (config.resume_path.stem if config.resume_path else "profile-driven")),
            "outdir": str(outdir),
            "cluster_count": 0,
            "confidence_floor": 0.0,
            "insufficient_signal": True,
        },
    )
    return {"outdir": str(outdir), "cluster_count": 0, "insufficient_signal": True}


def _collect_used_evidence(clusters: list[dict]) -> list[dict]:
    output: list[dict] = []
    for cluster in clusters:
        for item in cluster.get("used_evidence", []):
            output.append({"cluster_id": cluster["cluster_id"], **item})
    return output
