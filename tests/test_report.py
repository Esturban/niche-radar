from __future__ import annotations

from niche_radar.report import render_insufficient_signal_report, render_report


def _cluster(
    cluster_id: str,
    *,
    title: str,
    evidence_strength: float,
    specificity: float,
    confidence: float,
    profile_fit: float,
    recommended_cluster: bool,
    recommended_bet: bool = True,
    questions: list[str] | None = None,
    related_terms: list[str] | None = None,
    evidence_titles: list[str] | None = None,
    workflow_or_pain: str | None = None,
    wedge_label: str | None = None,
    dossier: dict | None = None,
) -> dict:
    evidence_items = [
        {
            "title": item,
            "url": f"https://example.com/{index}",
            "snippet": f"{item} snippet",
        }
        for index, item in enumerate(evidence_titles or [], start=1)
    ]
    return {
        "cluster_id": cluster_id,
        "title": title,
        "title_seed": title,
        "terms": [title, f"{title} template", f"{title} workflow"],
        "lineage_roots": [title],
        "generations": [0, 1, 2],
        "questions": questions or [],
        "related_terms": related_terms or [],
        "trusted_terms": [title],
        "trusted_questions": [item for item in (questions or []) if "software engineer" not in item and "consultant" not in item],
        "trusted_related_terms": [item for item in (related_terms or []) if "consultant" not in item and "template" not in item],
        "supporting_related_terms": related_terms or [],
        "trusted_signal_score": 0.75,
        "supporting_signal_score": 0.22,
        "noise_penalty": 0.0,
        "packaging_penalty": 0.12,
        "founder_readiness_score": 0.81 if recommended_cluster else 0.42,
        "founder_recommendable": recommended_cluster,
        "founder_rejection_reasons": [] if recommended_cluster else ["too broad"],
        "micro_wedges": [
            {
                "label": wedge_label or f"{title} for operators",
                "workflow_or_pain": workflow_or_pain or title,
                "supporting_terms": [title, f"{title} template"],
                "supporting_questions": questions or [],
                "evidence_refs": [
                    {"title": item["title"], "url": item["url"], "signal_class": "trusted_workflow"}
                    for item in evidence_items[:3]
                ],
                "advice": f"Start with {title}.",
            }
        ],
        "recommended_wedge": {
            "label": wedge_label or f"{title} for operators",
            "workflow_or_pain": workflow_or_pain or title,
            "supporting_terms": [title, f"{title} template"],
            "supporting_questions": questions or [],
            "evidence_refs": [
                {"title": item["title"], "url": item["url"], "signal_class": "trusted_workflow"}
                for item in evidence_items[:3]
            ],
            "advice": f"Start with {title}.",
        },
        "used_evidence": [{**item, "signal_class": "trusted_workflow"} for item in evidence_items],
        "evidence_tier": "strong" if evidence_strength >= 0.7 else "moderate",
        "evidence_strength": evidence_strength,
        "citation_count": len(evidence_items),
        "surface_count": 2,
        "profile_fit_score": profile_fit,
        "trend_strength": 0.0,
        "recency_support": 0.0,
        "specificity_score": specificity,
        "focus_score": 1.0,
        "focus_gate": True,
        "evidence_gate": True,
        "brief_alignment_score": 0.2,
        "evidence_types": ["search_adjacent", "external_evidence"],
        "confidence": confidence,
        "research_score": 0.0,
        "dossier": dossier or {},
        "recommendation_failure_reasons": [],
        "recommended_cluster": recommended_cluster,
        "recommended_bet": recommended_bet,
        "advice": f"Start with {title}.",
        "suggested_wedge": f"Start with {title}.",
    }


def test_render_report_starts_with_founder_memo_and_concrete_actions():
    winner = _cluster(
        "winner",
        title="shopify operations automation",
        wedge_label="shopify operations automation templates for operators",
        workflow_or_pain="shopify operations automation",
        evidence_strength=0.76,
        specificity=0.84,
        confidence=0.71,
        profile_fit=0.35,
        recommended_cluster=True,
        questions=[
            "shopify operations automation templates",
            "shopify operations automation software templates",
        ],
        related_terms=[
            "shopify operations automation templates",
            "shopify operations automation tutorial",
        ],
        evidence_titles=[
            "Workflow Automation made easy with Shopify Flow",
            "Shopify Flow Examples: 20+ Automation Workflows You Can Copy Today",
        ],
    )
    near_miss = _cluster(
        "near-miss",
        title="shopify operations automation dashboard",
        evidence_strength=0.63,
        specificity=0.81,
        confidence=0.58,
        profile_fit=0.33,
        recommended_cluster=False,
        questions=["shopify operations automation dashboard templates"],
        related_terms=["shopify operations automation dashboard tutorial"],
        evidence_titles=["Dev Dashboard - Shopify Developers Platform"],
    )

    run_meta = {
        "focus": "shopify operations automation",
        "run_schema_version": 2,
        "policy_version": "founder_wedge_v1",
        "confidence_floor": 0.58,
        "wedge_summary": {"recommended_bet_count": 2, "specificity_outcome": "recommended_bets_found"},
        "research_summary": {"depth": "standard"},
        "focus_summary": {"threshold": 0.34, "accepted_clusters": [{"cluster": winner["title"]}]},
        "evidence_summary": {"required_types": ["search_adjacent", "external_evidence"], "accepted_clusters": [{"cluster": winner["title"]}]},
        "recommendation_context": {"brief": "Prefer a narrow ops wedge."},
        "brief_influence": {"winner_changed": False},
        "recommended_cluster_id": "winner",
        "recommended_cluster_title": winner["title"],
    }

    report = render_report([winner, near_miss], [], run_meta)

    assert "## Founder memo" in report
    assert "### Recommended niche" in report
    assert "Shopify operators dealing with repeated operations work that teams are still patching by hand." in report
    assert "### Why this is worth testing" in report
    assert "### Why this won over the near-misses" in report
    assert "### Next 3 validation conversations/tests" in report
    assert "1. Target:" in report
    assert "2. Target:" in report
    assert "3. Target:" in report
    assert "software engineer" not in report
    assert "consultants" not in report
    assert "## Appendix" in report


def test_render_report_keeps_founder_memo_useful_without_dossier():
    winner = _cluster(
        "winner",
        title="shopify operations automation reporting",
        workflow_or_pain="shopify operations automation reporting",
        evidence_strength=0.72,
        specificity=0.77,
        confidence=0.69,
        profile_fit=0.22,
        recommended_cluster=True,
        questions=["shopify operations automation reporting templates"],
        related_terms=["shopify operations automation reporting tutorial"],
        evidence_titles=["Automating Shopify Reports: Tools and Techniques for Regular Insights"],
        dossier={},
    )
    run_meta = {
        "focus": "shopify operations automation",
        "run_schema_version": 2,
        "policy_version": "founder_wedge_v1",
        "confidence_floor": 0.69,
        "wedge_summary": {"recommended_bet_count": 1, "specificity_outcome": "recommended_bets_found"},
        "research_summary": {"depth": "off"},
        "focus_summary": {"threshold": 0.34, "accepted_clusters": [{"cluster": winner["title"]}]},
        "evidence_summary": {"required_types": ["search_adjacent", "external_evidence"], "accepted_clusters": [{"cluster": winner["title"]}]},
        "recommendation_context": {"brief": ""},
        "brief_influence": {"winner_changed": False},
        "recommended_cluster_id": "winner",
        "recommended_cluster_title": winner["title"],
    }

    report = render_report([winner], [], run_meta)

    assert "manual reporting, recurring exports, and ops review prep" in report
    assert "No dossier summary generated." in report
    assert "Distinct evidence pages keep pointing at the same workflow" in report


def test_render_insufficient_signal_report_uses_founder_no_call_contract():
    report = render_insufficient_signal_report(
        focus="shopify operations automation",
        seeds=["shopify operations automation", "shopify reporting"],
        reasons=["youtube disabled", "google trends returned 429"],
        brief="Prefer an ops wedge I can test quickly.",
    )

    assert "## Founder memo" in report
    assert "No call." in report
    assert "### What this does not prove" in report
    assert "### Next 3 validation conversations/tests" in report
    assert "shopify operations automation" in report
