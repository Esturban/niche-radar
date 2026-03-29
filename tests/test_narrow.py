from __future__ import annotations

from niche_radar.narrow import attach_micro_wedges
from niche_radar.rank import score_clusters


def test_attach_micro_wedges_extracts_evidence_backed_candidate():
    cluster = {
        "cluster_id": "small business reporting",
        "title_seed": "small business reporting",
        "terms": [
            "small business reporting",
            "monthly reporting automation",
            "client reporting template",
        ],
        "items": [
            {
                "term": "small business reporting",
                "generation": 0,
                "lineage_root": "small business reporting",
                "providers": ["google_suggest"],
                "trend_strength_raw": 0.5,
                "trend_velocity_raw": 0.2,
                "surface_spread_raw": 1.0,
            }
        ],
        "lineage_roots": ["small business reporting"],
        "generations": [0, 1],
        "questions": [
            "small business reporting software",
            "monthly reporting automation for small business",
        ],
        "related_terms": [
            "client reporting template for small business",
            "monthly reporting automation for small businesses",
        ],
    }
    evidence_by_cluster = {
        "small business reporting": {
            "items": [
                {
                    "title": "Monthly reporting automation for small business teams",
                    "url": "https://example.com/monthly-reporting",
                    "snippet": "Monthly reporting automation helps small businesses replace manual spreadsheet reporting with a client reporting template and lightweight reporting software.",
                    "matched_terms": ["monthly", "reporting", "automation", "template", "software"],
                }
            ]
        }
    }

    [enriched] = attach_micro_wedges([cluster], evidence_by_cluster)

    assert enriched["recommended_bet"] is True
    wedge = enriched["recommended_wedge"]
    assert wedge is not None
    assert "reporting" in wedge["label"]
    assert wedge["rejection_reason"] is None
    assert wedge["evidence_refs"]
    assert wedge["specificity_score"] >= 0.58


def test_attach_micro_wedges_refuses_false_precision_for_broad_cluster():
    cluster = {
        "cluster_id": "small business automation",
        "title_seed": "small business automation",
        "terms": ["small business automation", "automation for small business"],
        "items": [
            {
                "term": "small business automation",
                "generation": 0,
                "lineage_root": "small business automation",
                "providers": ["google_suggest"],
                "trend_strength_raw": 0.5,
                "trend_velocity_raw": 0.2,
                "surface_spread_raw": 1.0,
            }
        ],
        "lineage_roots": ["small business automation"],
        "generations": [0, 1],
        "questions": ["automation for small business"],
        "related_terms": ["small business automation ideas"],
    }
    evidence_by_cluster = {
        "small business automation": {
            "items": [
                {
                    "title": "Small business automation guide",
                    "url": "https://example.com/automation",
                    "snippet": "Small business automation guide with general workflow ideas.",
                    "matched_terms": ["automation"],
                }
            ]
        }
    }

    [enriched] = attach_micro_wedges([cluster], evidence_by_cluster)

    assert enriched["recommended_bet"] is False
    assert enriched["recommended_wedge"] is None
    assert enriched["micro_wedges"]
    assert enriched["micro_wedges"][0]["rejection_reason"] in {"too broad", "weak evidence", "low specificity"}


def test_score_clusters_prefers_specific_bet_when_supported():
    narrow_cluster = {
        "cluster_id": "small business reporting",
        "title_seed": "small business reporting",
        "title": "small business reporting",
        "terms": ["small business reporting", "monthly reporting automation"],
        "items": [
            {
                "term": "small business reporting",
                "generation": 0,
                "lineage_root": "small business reporting",
                "providers": ["google_suggest", "youtube"],
                "trend_strength_raw": 0.4,
                "trend_velocity_raw": 0.2,
                "surface_spread_raw": 1.0,
            }
        ],
        "lineage_roots": ["small business reporting"],
        "generations": [0, 1],
        "questions": ["small business reporting software"],
        "related_terms": ["monthly reporting automation for small businesses"],
        "recommended_bet": True,
        "specificity_score": 0.78,
        "recommended_wedge": {
            "label": "monthly reporting automation for small businesses",
            "advice": "Start with a workflow pack.",
        },
        "micro_wedges": [{"label": "monthly reporting automation for small businesses", "specificity_score": 0.78, "rejection_reason": None}],
    }
    broad_cluster = {
        "cluster_id": "small business automation",
        "title_seed": "small business automation",
        "title": "small business automation",
        "terms": ["small business automation"],
        "items": [
            {
                "term": "small business automation",
                "generation": 0,
                "lineage_root": "small business automation",
                "providers": ["google_suggest", "youtube"],
                "trend_strength_raw": 0.6,
                "trend_velocity_raw": 0.2,
                "surface_spread_raw": 1.0,
            }
        ],
        "lineage_roots": ["small business automation"],
        "generations": [0, 1],
        "questions": ["small business automation"],
        "related_terms": ["small business automation ideas"],
        "recommended_bet": False,
        "specificity_score": 0.12,
        "recommended_wedge": None,
        "micro_wedges": [{"label": "small business automation", "specificity_score": 0.12, "rejection_reason": "too broad"}],
    }
    evidence_by_cluster = {
        "small business reporting": {
            "items": [
                {
                    "title": "Monthly reporting automation guide",
                    "url": "https://example.com/reporting",
                    "snippet": "Monthly reporting automation is replacing manual spreadsheet work for small teams.",
                    "matched_terms": ["monthly", "reporting", "automation"],
                }
            ],
            "citation_count": 1,
            "snippet_quality_raw": 0.9,
            "recency_support_raw": 1.0,
        },
        "small business automation": {
            "items": [
                {
                    "title": "Small business automation guide",
                    "url": "https://example.com/automation",
                    "snippet": "General automation ideas.",
                    "matched_terms": ["automation"],
                }
            ],
            "citation_count": 1,
            "snippet_quality_raw": 0.6,
            "recency_support_raw": 1.0,
        },
    }

    ranked, _ = score_clusters(
        clusters=[broad_cluster, narrow_cluster],
        profile={"keywords": ["reporting", "automation"], "phrases": [], "themes": []},
        total_generations=3,
        topic="small business operations",
        evidence_by_cluster=evidence_by_cluster,
    )

    assert ranked[0]["cluster_id"] == "small business reporting"
