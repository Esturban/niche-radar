from __future__ import annotations

from niche_radar.recommend import apply_recommendation_policy, build_recommendation_context


def _candidate(cluster_id: str, *, evidence: float, specificity: float, fit: float, title: str, terms: list[str]) -> dict:
    return {
        "cluster_id": cluster_id,
        "title": title,
        "title_seed": title,
        "terms": terms,
        "related_terms": [],
        "questions": [],
        "recommended_bet": True,
        "evidence_strength": evidence,
        "specificity_score": specificity,
        "profile_fit_score": fit,
        "confidence": 0.6,
        "total_score": 0.6,
    }


def test_build_recommendation_context_normalizes_and_caps_brief():
    context = build_recommendation_context(
        focus="shopify ecommerce",
        brief="  " + ("service business workflows " * 20) + "  ",
    )

    assert context["focus"] == "shopify ecommerce"
    assert context["brief"].endswith("...")
    assert context["brief_truncated"] is True
    assert context["brief_token_count"] > 0


def test_apply_recommendation_policy_keeps_evidence_first():
    context = build_recommendation_context(focus="shopify ecommerce", brief="service businesses")
    clusters = [
        _candidate(
            "strong",
            evidence=0.91,
            specificity=0.70,
            fit=0.55,
            title="shopify fulfillment automation",
            terms=["shopify fulfillment automation"],
        ),
        _candidate(
            "aligned",
            evidence=0.55,
            specificity=0.70,
            fit=0.55,
            title="service business onboarding",
            terms=["service business onboarding"],
        ),
    ]

    annotated, summary = apply_recommendation_policy(ranked_clusters=clusters, context=context)

    assert summary["recommended_cluster_id"] == "strong"
    assert any(cluster["recommended_cluster"] for cluster in annotated)
    assert summary["brief_influence"]["winner_changed"] is False


def test_apply_recommendation_policy_uses_brief_as_tiebreak():
    context = build_recommendation_context(focus="shopify ecommerce", brief="onboarding services")
    clusters = [
        _candidate(
            "generic",
            evidence=0.80,
            specificity=0.70,
            fit=0.60,
            title="shopify reporting automation",
            terms=["shopify reporting automation"],
        ),
        _candidate(
            "brief-match",
            evidence=0.80,
            specificity=0.70,
            fit=0.60,
            title="shopify onboarding services",
            terms=["shopify onboarding services"],
        ),
    ]

    _, summary = apply_recommendation_policy(ranked_clusters=clusters, context=context)

    assert summary["recommended_cluster_id"] == "brief-match"
    assert summary["brief_influence"]["winner_changed"] is True
