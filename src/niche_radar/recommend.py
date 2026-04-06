from __future__ import annotations

import re

from .signal_quality import is_generic_parent_phrase
from .utils import content_tokens

MAX_BRIEF_CHARS = 280
RUN_SCHEMA_VERSION = 2
POLICY_VERSION = "founder_wedge_v1"


def build_recommendation_context(*, focus: str, brief: str) -> dict:
    normalized_brief, truncated = _normalize_brief(brief)
    return {
        "focus": focus,
        "brief": normalized_brief,
        "brief_truncated": truncated,
        "brief_token_count": len(content_tokens(normalized_brief)),
    }


def apply_recommendation_policy(*, ranked_clusters: list[dict], context: dict) -> tuple[list[dict], dict]:
    annotated = []
    for cluster in ranked_clusters:
        annotated.append(
            {
                **cluster,
                "brief_alignment_score": round(_brief_alignment_score(cluster=cluster, brief=context.get("brief", "")), 4),
                "recommended_cluster": False,
            }
        )

    candidates = [
        cluster
        for cluster in annotated
        if cluster.get("founder_recommendable", cluster.get("recommended_bet", False))
    ]
    baseline = _pick_highlighted_cluster(candidates=candidates, use_brief=False)
    winner = _pick_highlighted_cluster(candidates=candidates, use_brief=bool(context.get("brief")))
    winner_id = winner.get("cluster_id") if winner else None

    output = []
    for cluster in annotated:
        output.append({**cluster, "recommended_cluster": cluster.get("cluster_id") == winner_id})

    return output, {
        "run_schema_version": RUN_SCHEMA_VERSION,
        "policy_version": POLICY_VERSION,
        "recommended_cluster_id": winner_id,
        "recommended_cluster_title": winner.get("title") if winner else None,
        "recommended_call_type": "winner" if winner else "no_call",
        "founder_readiness_score": winner.get("founder_readiness_score", 0.0) if winner else 0.0,
        "founder_rejection_reasons": winner.get("founder_rejection_reasons", []) if winner else [],
        "trusted_signal_summary": (
            {
                "trusted_questions": winner.get("trusted_questions", [])[:4],
                "trusted_related_terms": winner.get("trusted_related_terms", [])[:4],
                "trusted_terms": winner.get("trusted_terms", [])[:4],
            }
            if winner
            else {}
        ),
        "recommendation_context": context,
        "brief_influence": {
            "applied": bool(context.get("brief")),
            "mode": "tiebreak_and_narrative_only",
            "baseline_recommended_cluster_id": baseline.get("cluster_id") if baseline else None,
            "winner_changed": bool(baseline and winner and baseline.get("cluster_id") != winner.get("cluster_id")),
            "selected_brief_alignment_score": winner.get("brief_alignment_score", 0.0) if winner else 0.0,
        },
    }


def _pick_highlighted_cluster(*, candidates: list[dict], use_brief: bool) -> dict | None:
    if not candidates:
        return None
    winner = max(candidates, key=lambda cluster: _winner_sort_key(cluster=cluster, use_brief=use_brief))
    for cluster in candidates:
        if cluster.get("cluster_id") == winner.get("cluster_id"):
            continue
        if _prefer_more_concrete_child(current=winner, challenger=cluster):
            winner = cluster
    return winner


def _winner_sort_key(*, cluster: dict, use_brief: bool) -> tuple:
    return (
        round(float(cluster.get("founder_readiness_score", 0.0)), 4),
        round(float(cluster.get("evidence_strength", 0.0)), 4),
        round(float(cluster.get("specificity_score", 0.0)), 4),
        round(float(cluster.get("profile_fit_score", 0.0)), 4),
        round(float(cluster.get("brief_alignment_score", 0.0)), 4) if use_brief else -1.0,
        round(float(cluster.get("confidence", 0.0)), 4),
        round(float(cluster.get("total_score", 0.0)), 4),
        cluster.get("title", cluster.get("title_seed", "")),
    )


def _prefer_more_concrete_child(*, current: dict, challenger: dict) -> bool:
    current_evidence = float(current.get("evidence_strength", 0.0))
    challenger_evidence = float(challenger.get("evidence_strength", 0.0))
    if abs(current_evidence - challenger_evidence) > 0.05:
        return False

    current_readiness = float(current.get("founder_readiness_score", 0.0))
    challenger_readiness = float(challenger.get("founder_readiness_score", 0.0))
    if challenger_readiness < current_readiness + 0.08:
        return False

    current_title = current.get("title_seed", current.get("title", ""))
    challenger_title = challenger.get("title_seed", challenger.get("title", ""))
    return is_generic_parent_phrase(current_title) and not is_generic_parent_phrase(challenger_title)


def _brief_alignment_score(*, cluster: dict, brief: str) -> float:
    brief_tokens = set(content_tokens(brief))
    if not brief_tokens:
        return 0.0

    cluster_tokens = set(
        token
        for value in [
            cluster.get("title", ""),
            cluster.get("title_seed", ""),
            *cluster.get("terms", [])[:8],
            *cluster.get("related_terms", [])[:6],
            *cluster.get("questions", [])[:4],
        ]
        for token in content_tokens(value)
    )
    if not cluster_tokens:
        return 0.0
    return len(brief_tokens & cluster_tokens) / len(brief_tokens)


def _normalize_brief(brief: str) -> tuple[str, bool]:
    cleaned = re.sub(r"\s+", " ", (brief or "").strip())
    if not cleaned:
        return "", False
    if len(cleaned) <= MAX_BRIEF_CHARS:
        return cleaned, False
    return cleaned[: MAX_BRIEF_CHARS - 3].rstrip() + "...", True
