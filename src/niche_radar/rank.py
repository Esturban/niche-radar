from __future__ import annotations

from .evolve import lineage_generations
from .signal_quality import is_generic_parent_phrase
from .utils import clamp01, content_tokens, minmax_scale, safe_mean


def score_clusters(
    clusters: list[dict],
    profile: dict,
    total_generations: int,
    topic: str,
    evidence_by_cluster: dict[str, dict] | None = None,
) -> tuple[list[dict], list[dict]]:
    evidence_by_cluster = evidence_by_cluster or {}
    profile_vocab = {
        token
        for value in profile.get("keywords", []) + profile.get("phrases", []) + profile.get("themes", [])
        for token in content_tokens(value)
    }
    topic_vocab = set(content_tokens(topic))
    small_business_mode = "small business" in topic.lower()
    lineage_map = lineage_generations(
        [
            # reconstructed light-weight records
            type("Record", (), {"lineage_root": item["lineage_root"], "generation": item["generation"]})
            for cluster in clusters
            for item in cluster["items"]
        ]
    )

    raw_fit: dict[str, float] = {}
    raw_strength: dict[str, float] = {}
    raw_velocity: dict[str, float] = {}
    raw_adjacency: dict[str, float] = {}
    raw_question: dict[str, float] = {}
    raw_surface: dict[str, float] = {}
    raw_survival: dict[str, float] = {}
    raw_context: dict[str, float] = {}
    raw_citations: dict[str, float] = {}
    raw_evidence_quality: dict[str, float] = {}
    raw_recency: dict[str, float] = {}
    raw_surface_count: dict[str, float] = {}
    raw_specificity: dict[str, float] = {}
    raw_trusted_signal: dict[str, float] = {}
    raw_supporting_signal: dict[str, float] = {}
    raw_noise_penalty: dict[str, float] = {}
    raw_packaging_penalty: dict[str, float] = {}
    raw_trusted_evidence: dict[str, float] = {}

    for cluster in clusters:
        cluster_id = cluster["cluster_id"]
        tokens = set(token for term in cluster["terms"] for token in content_tokens(term))
        evidence = evidence_by_cluster.get(cluster_id, {})
        provider_count = len({provider for item in cluster["items"] for provider in item.get("providers", [])})

        raw_fit[cluster_id] = len(tokens & profile_vocab) / max(1, len(tokens))
        raw_strength[cluster_id] = max(item.get("trend_strength_raw", 0.0) for item in cluster["items"])
        raw_velocity[cluster_id] = max(item.get("trend_velocity_raw", 0.0) for item in cluster["items"])
        raw_adjacency[cluster_id] = float(len(cluster["related_terms"]))
        raw_question[cluster_id] = float(len(cluster["questions"]))
        raw_surface[cluster_id] = safe_mean(item.get("surface_spread_raw", 0.0) for item in cluster["items"])
        raw_surface_count[cluster_id] = float(provider_count + (1 if evidence.get("items") else 0))
        survivals = [len(lineage_map.get(root, set())) / max(1, total_generations) for root in cluster["lineage_roots"]]
        raw_survival[cluster_id] = safe_mean(survivals)
        raw_citations[cluster_id] = float(evidence.get("citation_count", 0))
        raw_evidence_quality[cluster_id] = float(evidence.get("snippet_quality_raw", 0.0))
        raw_recency[cluster_id] = float(evidence.get("recency_support_raw", 0.0))
        raw_specificity[cluster_id] = float(cluster.get("specificity_score", 0.0))
        raw_trusted_signal[cluster_id] = float(cluster.get("trusted_signal_score", 0.0))
        raw_supporting_signal[cluster_id] = float(cluster.get("supporting_signal_score", 0.0))
        raw_noise_penalty[cluster_id] = float(cluster.get("noise_penalty", 0.0))
        raw_packaging_penalty[cluster_id] = float(cluster.get("packaging_penalty", 0.0))
        citation_count = max(1, int(evidence.get("citation_count", 0)))
        raw_trusted_evidence[cluster_id] = float(evidence.get("trusted_evidence_count", 0)) / citation_count
        context_hits = 0
        context_total = 0
        for value in cluster["terms"] + cluster["related_terms"][:10] + cluster["questions"][:6]:
            lowered = value.lower()
            context_total += 1
            if set(content_tokens(value)) & topic_vocab:
                context_hits += 1
                continue
            if small_business_mode and "small business" in lowered:
                context_hits += 1
        raw_context[cluster_id] = context_hits / max(1, context_total)

    fit = {key: clamp01(value) for key, value in raw_fit.items()}
    strength = minmax_scale(raw_strength)
    velocity = minmax_scale(raw_velocity)
    adjacency = minmax_scale(raw_adjacency)
    question = minmax_scale(raw_question)
    surface = minmax_scale(raw_surface)
    survival = minmax_scale(raw_survival)
    context = {key: clamp01(value) for key, value in raw_context.items()}
    citations = minmax_scale(raw_citations)
    evidence_quality = {key: clamp01(value) for key, value in raw_evidence_quality.items()}
    recency = {key: clamp01(value) for key, value in raw_recency.items()}
    surface_count = minmax_scale(raw_surface_count)
    specificity = {key: clamp01(value) for key, value in raw_specificity.items()}
    trusted_signal = {key: clamp01(value) for key, value in raw_trusted_signal.items()}
    supporting_signal = {key: clamp01(value) for key, value in raw_supporting_signal.items()}
    noise_penalty = {key: clamp01(value) for key, value in raw_noise_penalty.items()}
    packaging_penalty = {key: clamp01(value) for key, value in raw_packaging_penalty.items()}
    trusted_evidence = {key: clamp01(value) for key, value in raw_trusted_evidence.items()}

    scored: list[dict] = []
    for cluster in clusters:
        cluster_id = cluster["cluster_id"]
        evidence = evidence_by_cluster.get(cluster_id, {})
        evidence_strength = clamp01(
            citations.get(cluster_id, 0.0) * 0.40
            + evidence_quality.get(cluster_id, 0.0) * 0.25
            + surface_count.get(cluster_id, 0.0) * 0.15
            + strength.get(cluster_id, 0.0) * 0.10
            + recency.get(cluster_id, 0.0) * 0.10
        )
        confidence = clamp01(
            (
                evidence_strength
                + fit.get(cluster_id, 0.0)
                + strength.get(cluster_id, 0.0)
                + adjacency.get(cluster_id, 0.0)
                + surface.get(cluster_id, 0.0)
                + survival.get(cluster_id, 0.0)
                + context.get(cluster_id, 0.0)
                + specificity.get(cluster_id, 0.0)
                + trusted_signal.get(cluster_id, 0.0)
            )
            / 9
        )
        total_score = clamp01(
            evidence_strength * 0.28
            + specificity.get(cluster_id, 0.0) * 0.18
            + fit.get(cluster_id, 0.0) * 0.14
            + context.get(cluster_id, 0.0) * 0.12
            + strength.get(cluster_id, 0.0) * 0.08
            + velocity.get(cluster_id, 0.0) * 0.06
            + survival.get(cluster_id, 0.0) * 0.06
            + adjacency.get(cluster_id, 0.0) * 0.04
            + question.get(cluster_id, 0.0) * 0.04
            + surface.get(cluster_id, 0.0) * 0.04
        )
        founder_rejection_reasons: list[str] = list(cluster.get("founder_rejection_reasons", []))
        if trusted_signal.get(cluster_id, 0.0) < 0.25:
            founder_rejection_reasons.append("not enough trusted workflow signal")
        if trusted_evidence.get(cluster_id, 0.0) <= 0.0:
            founder_rejection_reasons.append("no trusted evidence anchors")
        if is_generic_parent_phrase(cluster.get("title_seed", "")):
            founder_rejection_reasons.append("generic parent cluster")
        founder_rejection_reasons = list(dict.fromkeys(founder_rejection_reasons))
        founder_readiness = clamp01(
            trusted_signal.get(cluster_id, 0.0) * 0.34
            + trusted_evidence.get(cluster_id, 0.0) * 0.26
            + specificity.get(cluster_id, 0.0) * 0.18
            + evidence_strength * 0.12
            + fit.get(cluster_id, 0.0) * 0.06
            + context.get(cluster_id, 0.0) * 0.04
            - packaging_penalty.get(cluster_id, 0.0) * 0.22
            - noise_penalty.get(cluster_id, 0.0) * 0.28
        )
        founder_recommendable = (
            bool(cluster.get("recommended_bet"))
            and not founder_rejection_reasons
            and founder_readiness >= 0.58
        )
        scored.append(
            {
                **cluster,
                "title": cluster["title_seed"],
                "evidence": evidence.get("items", []),
                "evidence_provider": evidence.get("provider"),
                "evidence_query": evidence.get("query"),
                "evidence_strength": round(evidence_strength, 4),
                "evidence_tier": _evidence_tier(evidence_strength),
                "citation_count": int(raw_citations.get(cluster_id, 0.0)),
                "surface_count": int(raw_surface_count.get(cluster_id, 0.0)),
                "profile_fit_score": round(fit.get(cluster_id, 0.0), 4),
                "trend_strength": round(strength.get(cluster_id, 0.0), 4),
                "trend_velocity": round(velocity.get(cluster_id, 0.0), 4),
                "batch_survival_score": round(survival.get(cluster_id, 0.0), 4),
                "adjacency_score": round(adjacency.get(cluster_id, 0.0), 4),
                "question_density": round(question.get(cluster_id, 0.0), 4),
                "surface_spread": round(surface.get(cluster_id, 0.0), 4),
                "context_relevance": round(context.get(cluster_id, 0.0), 4),
                "trend_support": round(strength.get(cluster_id, 0.0), 4),
                "recency_support": round(recency.get(cluster_id, 0.0), 4),
                "specificity_score": round(specificity.get(cluster_id, 0.0), 4),
                "trusted_signal_score": round(trusted_signal.get(cluster_id, 0.0), 4),
                "supporting_signal_score": round(supporting_signal.get(cluster_id, 0.0), 4),
                "noise_penalty": round(noise_penalty.get(cluster_id, 0.0), 4),
                "packaging_penalty": round(packaging_penalty.get(cluster_id, 0.0), 4),
                "founder_readiness_score": round(founder_readiness, 4),
                "founder_recommendable": founder_recommendable,
                "founder_rejection_reasons": founder_rejection_reasons,
                "trusted_evidence_count": int(evidence.get("trusted_evidence_count", 0)),
                "confidence": round(confidence, 4),
                "total_score": round(total_score, 4),
                "suggested_wedge": (cluster.get("recommended_wedge") or {}).get("advice") or _suggested_wedge(cluster, evidence.get("items", [])),
                "validation_needed": True,
                "competition_surface_proxy": None,
            }
        )

    ranked = sorted(
        scored,
        key=lambda cluster: (
            cluster.get("founder_recommendable", False),
            cluster.get("founder_readiness_score", 0.0),
            cluster.get("specificity_score", 0.0),
            cluster["evidence_strength"],
            cluster["confidence"],
            cluster["profile_fit_score"],
            cluster["total_score"],
        ),
        reverse=True,
    )
    return ranked, scored


def _evidence_tier(value: float) -> str:
    if value >= 0.67:
        return "strong"
    if value >= 0.45:
        return "moderate"
    if value >= 0.25:
        return "weak"
    return "speculative"


def _suggested_wedge(cluster: dict, evidence_items: list[dict]) -> str:
    title = cluster["title_seed"]
    if evidence_items:
        top_item = evidence_items[0]
        matched_terms = ", ".join(top_item.get("matched_terms", [])[:3])
        if matched_terms:
            return f"Start with a service or workflow pack for `{title}` anchored on {matched_terms}."
        return f"Start with a proof-of-work offer for `{title}` and use the cited evidence to shape the first deliverable."
    if cluster["questions"]:
        return f"Build a lightweight guide, workflow pack, or service around `{title}` that answers the top recurring questions first."
    return f"Explore a content-led or service-led wedge around `{title}` before building software."
