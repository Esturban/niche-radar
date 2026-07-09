from __future__ import annotations

from copy import deepcopy

from ..collect import collect_evidence_search
from ..utils import clamp01, dedupe_preserve_order
from .provider import make_research_provider

DEPTH_BUDGETS = {
    "off": {"queries": 0, "pages": 0},
    "standard": {"queries": 2, "pages": 2},
    "deep": {"queries": 4, "pages": 3},
}
MIN_RESEARCH_EVIDENCE = 2


def apply_research_graph(
    *,
    ranked_clusters: list[dict],
    focus: str,
    research_depth: str,
    research_top_k: int,
    evidence_pages: int,
    llm_provider: str,
) -> tuple[list[dict], dict]:
    depth = (research_depth or "standard").strip().lower()
    if depth not in DEPTH_BUDGETS:
        raise ValueError(f"unsupported research depth: {research_depth}")
    if depth == "off" or research_top_k <= 0:
        return ranked_clusters, {"depth": depth, "entries": [], "provider": None}

    provider = make_research_provider(llm_provider)
    shortlisted_ids = {cluster["cluster_id"] for cluster in ranked_clusters[:research_top_k]}
    traces: list[dict] = []
    updated: list[dict] = []

    for cluster in ranked_clusters:
        if cluster["cluster_id"] not in shortlisted_ids:
            stale = deepcopy(cluster)
            stale["research"] = _default_research_payload("not_shortlisted")
            updated.append(stale)
            continue

        enriched, trace = _research_cluster(
            cluster=cluster,
            focus=focus,
            provider=provider,
            budget=DEPTH_BUDGETS[depth],
            evidence_pages=evidence_pages,
        )
        updated.append(enriched)
        traces.append(trace)

    reranked = _rerank_clusters(updated)
    return reranked, {"depth": depth, "entries": traces, "provider": llm_provider}


def _research_cluster(*, cluster: dict, focus: str, provider, budget: dict[str, int], evidence_pages: int) -> tuple[dict, dict]:
    shortlisted = deepcopy(cluster)
    scout = _scout_cluster(
        cluster=shortlisted,
        focus=focus,
        provider=provider,
        max_queries=budget["queries"],
        evidence_pages=min(budget["pages"], evidence_pages),
    )
    skeptic = _skeptic_review(cluster=shortlisted, scout=scout)
    dossier = _editor_card(cluster=shortlisted, scout=scout, skeptic=skeptic)
    research_score = clamp01(scout["score"] * 0.45 + skeptic["score"] * 0.55)
    final_score = clamp01(shortlisted.get("total_score", 0.0) * 0.65 + research_score * 0.35)

    shortlisted["research"] = {
        "score": round(research_score, 4),
        "final_score": round(final_score, 4),
        "queries": scout["queries"],
        "penalties": skeptic["penalties"],
        "notes": skeptic["notes"],
        "status": "ok",
    }
    shortlisted["dossier"] = dossier
    shortlisted["total_score"] = round(final_score, 4)
    shortlisted["used_evidence"] = dossier["citations"]
    shortlisted["research_score"] = round(research_score, 4)
    shortlisted["research_verdict"] = dossier["verdict"]

    trace = {
        "cluster_id": shortlisted["cluster_id"],
        "title": shortlisted["title"],
        "scout": scout,
        "skeptic": skeptic,
        "editor": dossier,
    }
    return shortlisted, trace


def _scout_cluster(*, cluster: dict, focus: str, provider, max_queries: int, evidence_pages: int) -> dict:
    if max_queries <= 0 or evidence_pages <= 0:
        return {"queries": [], "items": [], "score": 0.0}

    heuristic_queries = _heuristic_queries(cluster=cluster, focus=focus)
    llm_queries = provider.generate_follow_up_queries(cluster=cluster, focus=focus)
    queries = dedupe_preserve_order(heuristic_queries + llm_queries)[:max_queries]
    existing_urls = {item.get("url") for item in cluster.get("evidence", []) if item.get("url")}
    items: list[dict] = []

    for index, query in enumerate(queries):
        synthetic_cluster = [{"cluster_id": f"{cluster['cluster_id']}::{index}", "title_seed": query}]
        evidence_payload = collect_evidence_search(
            clusters=synthetic_cluster,
            focus=focus,
            evidence_pages=evidence_pages,
        )
        query_items = evidence_payload.get(f"{cluster['cluster_id']}::{index}", {}).get("items", [])
        for item in query_items:
            if item.get("url") in existing_urls:
                continue
            item = {**item, "query": query}
            items.append(item)
            existing_urls.add(item.get("url"))

    score = clamp01(
        min(1.0, len(items) / max(1, max_queries * max(1, evidence_pages))) * 0.55
        + min(1.0, sum(item.get("quality_score", 0.0) for item in items) / max(1, len(items))) * 0.45
    )
    return {"queries": queries, "items": items[: max_queries * evidence_pages], "score": round(score, 4)}


def _heuristic_queries(*, cluster: dict, focus: str) -> list[str]:
    title = cluster.get("title") or cluster.get("title_seed") or ""
    wedge = (cluster.get("recommended_wedge") or {}).get("label", "")
    related = cluster.get("related_terms", [])[:3]
    questions = cluster.get("questions", [])[:2]
    queries = [
        f"{title} demand",
        f"{title} search volume",
    ]
    if wedge and wedge.lower() != title.lower():
        queries.append(wedge)
    queries.extend(related)
    queries.extend(questions)
    if focus and focus.lower() not in title.lower():
        queries.append(f"{title} {focus}".strip())
    return dedupe_preserve_order([query.strip() for query in queries if query.strip()])


def _skeptic_review(*, cluster: dict, scout: dict) -> dict:
    penalties: list[str] = []
    notes: list[str] = []
    score = 1.0

    specificity = float(cluster.get("specificity_score", 0.0))
    if specificity < 0.58:
        penalties.append("generic")
        notes.append("Specificity is below the founder-ready threshold.")
        score -= 0.35

    all_evidence = list(cluster.get("evidence", [])) + list(scout.get("items", []))
    if len(all_evidence) < MIN_RESEARCH_EVIDENCE:
        penalties.append("thin_evidence")
        notes.append("Fewer than two distinct evidence items support the niche.")
        score -= 0.30

    recency = [item.get("recency_score") for item in all_evidence if item.get("recency_score") is not None]
    if recency and (sum(recency) / len(recency)) < 0.35:
        penalties.append("stale")
        notes.append("Most evidence is old enough that trend confidence is weak.")
        score -= 0.20

    question_signals = len(cluster.get("questions", []))
    if question_signals == 0 and len(scout.get("items", [])) == 0:
        penalties.append("weak_demand_proxy")
        notes.append("There are no strong question-like or fresh evidence signals.")
        score -= 0.20

    if not penalties:
        notes.append("Research pass found enough evidence to keep the niche in contention.")
    return {"score": round(clamp01(score), 4), "penalties": penalties, "notes": notes}


def _editor_card(*, cluster: dict, scout: dict, skeptic: dict) -> dict:
    used_evidence = _select_used_evidence(cluster=cluster, scout=scout)
    label = (cluster.get("recommended_wedge") or {}).get("label") or cluster.get("title")
    verdict = "promote" if skeptic["score"] >= 0.55 else "hold"
    all_questions = cluster.get("questions", [])[:3]
    search_terms = dedupe_preserve_order(
        [item.get("query", "") for item in scout.get("items", []) if item.get("query")]
        + cluster.get("terms", [])[:3]
    )[:5]

    why_non_obvious = (
        f"`{label}` outperformed broader alternatives because it kept specificity "
        f"while preserving evidence strength `{cluster.get('evidence_strength', 0.0):.2f}`."
    )
    demand_summary = (
        f"Demand/search support comes from {len(used_evidence)} supporting citations and "
        f"{len(all_questions)} recurring question-like signals."
    )
    risk_summary = "; ".join(skeptic["notes"])
    next_action = (
        f"Test `{label}` with 3 founder conversations using the cited search and evidence patterns as prompts."
    )
    return {
        "niche": label,
        "verdict": verdict,
        "why_non_obvious": why_non_obvious,
        "demand_summary": demand_summary,
        "search_summary": ", ".join(search_terms) if search_terms else "No additional search terms captured.",
        "risk_summary": risk_summary,
        "next_action": next_action,
        "citations": used_evidence,
    }


def _select_used_evidence(*, cluster: dict, scout: dict) -> list[dict]:
    items = list(cluster.get("evidence", [])) + list(scout.get("items", []))
    ranked = sorted(
        items,
        key=lambda item: (
            item.get("quality_score", 0.0),
            item.get("recency_score", 0.0),
            len(item.get("matched_terms", [])),
        ),
        reverse=True,
    )
    compact = []
    seen: set[str] = set()
    for item in ranked:
        url = item.get("url", "")
        if not url or url in seen:
            continue
        seen.add(url)
        compact.append(
            {
                "title": item.get("title"),
                "url": url,
                "snippet": item.get("snippet"),
                "matched_terms": item.get("matched_terms", []),
                "query": item.get("query"),
            }
        )
        if len(compact) >= 4:
            break
    return compact


def _rerank_clusters(clusters: list[dict]) -> list[dict]:
    reviewed = [
        cluster
        for cluster in clusters
        if cluster.get("research", {}).get("status") != "not_shortlisted"
    ]
    untouched = [
        cluster
        for cluster in clusters
        if cluster.get("research", {}).get("status") == "not_shortlisted"
    ]
    reranked_reviewed = sorted(
        reviewed,
        key=lambda cluster: (
            cluster.get("research_verdict") == "promote",
            cluster.get("research_score", 0.0),
            cluster.get("recommended_bet", False),
            cluster.get("specificity_score", 0.0),
            cluster.get("evidence_strength", 0.0),
            cluster.get("total_score", 0.0),
        ),
        reverse=True,
    )
    return reranked_reviewed + untouched


def _default_research_payload(reason: str) -> dict:
    return {
        "score": 0.0,
        "final_score": 0.0,
        "queries": [],
        "penalties": [reason],
        "notes": ["Research graph did not run for this cluster."],
        "status": reason,
    }
