from __future__ import annotations

from niche_radar.research_graph.engine import apply_research_graph


class _FakeProvider:
    def __init__(self, queries: list[str]):
        self.queries = queries

    def generate_follow_up_queries(self, *, cluster: dict, focus: str) -> list[str]:
        return self.queries


def _ranked_clusters() -> list[dict]:
    return [
        {
            "cluster_id": "broad",
            "title": "small business automation",
            "title_seed": "small business automation",
            "terms": ["small business automation"],
            "questions": ["small business automation"],
            "related_terms": ["small business automation ideas"],
            "lineage_roots": ["small business automation"],
            "generations": [0, 1],
            "specificity_score": 0.18,
            "recommended_bet": False,
            "evidence_strength": 0.60,
            "total_score": 0.72,
            "confidence": 0.70,
            "evidence": [
                {
                    "title": "Broad automation guide",
                    "url": "https://example.com/broad",
                    "snippet": "General automation guide.",
                    "matched_terms": ["automation"],
                    "quality_score": 0.4,
                    "recency_score": 0.2,
                }
            ],
        },
        {
            "cluster_id": "narrow",
            "title": "small business reporting",
            "title_seed": "small business reporting",
            "terms": ["small business reporting", "monthly reporting automation"],
            "questions": ["monthly reporting automation for small business"],
            "related_terms": ["client reporting template for small businesses"],
            "lineage_roots": ["small business reporting"],
            "generations": [0, 1],
            "specificity_score": 0.81,
            "recommended_bet": True,
            "recommended_wedge": {"label": "monthly reporting automation for small businesses"},
            "evidence_strength": 0.58,
            "total_score": 0.68,
            "confidence": 0.66,
            "evidence": [
                {
                    "title": "Monthly reporting guide",
                    "url": "https://example.com/narrow",
                    "snippet": "Monthly reporting automation replaces manual spreadsheet work.",
                    "matched_terms": ["monthly", "reporting", "automation"],
                    "quality_score": 0.9,
                    "recency_score": 1.0,
                }
            ],
        },
        {
            "cluster_id": "untouched",
            "title": "small business dashboard",
            "title_seed": "small business dashboard",
            "terms": ["small business dashboard"],
            "questions": ["small business dashboard software"],
            "related_terms": ["dashboard workflow"],
            "lineage_roots": ["small business dashboard"],
            "generations": [0, 1],
            "specificity_score": 0.44,
            "recommended_bet": False,
            "evidence_strength": 0.42,
            "total_score": 0.40,
            "confidence": 0.45,
            "evidence": [],
        },
    ]


def test_apply_research_graph_reranks_only_shortlisted(monkeypatch):
    def fake_collect(clusters, focus, evidence_pages):
        query = clusters[0]["title_seed"]
        payload = {
            "provider": "test",
            "query": query,
            "items": [],
            "citation_count": 0,
            "snippet_quality_raw": 0.0,
            "recency_support_raw": 0.0,
        }
        if "reporting" in query:
            payload["items"] = [
                {
                    "title": "Reporting demand",
                    "url": "https://example.com/reporting-demand",
                    "snippet": "Reporting automation demand keeps rising.",
                    "matched_terms": ["reporting", "automation", "demand"],
                    "quality_score": 0.95,
                    "recency_score": 1.0,
                }
            ]
        return {clusters[0]["cluster_id"]: payload}

    monkeypatch.setattr("niche_radar.research_graph.engine.make_research_provider", lambda name: _FakeProvider(["reporting automation demand"]))
    monkeypatch.setattr("niche_radar.research_graph.engine.collect_evidence_search", fake_collect)

    reranked, trace = apply_research_graph(
        ranked_clusters=_ranked_clusters(),
        focus="small business operations",
        research_depth="standard",
        research_top_k=2,
        evidence_pages=2,
        llm_provider="openai",
    )

    assert reranked[0]["cluster_id"] == "narrow"
    assert reranked[-1]["cluster_id"] == "untouched"
    assert trace["entries"]


def test_apply_research_graph_adds_dossier_and_used_evidence(monkeypatch):
    monkeypatch.setattr("niche_radar.research_graph.engine.make_research_provider", lambda name: _FakeProvider([]))
    monkeypatch.setattr(
        "niche_radar.research_graph.engine.collect_evidence_search",
        lambda clusters, focus, evidence_pages: {clusters[0]["cluster_id"]: {"items": [], "provider": "test", "query": clusters[0]["title_seed"]}},
    )

    reranked, _ = apply_research_graph(
        ranked_clusters=_ranked_clusters(),
        focus="small business operations",
        research_depth="standard",
        research_top_k=1,
        evidence_pages=2,
        llm_provider="openai",
    )

    first = reranked[0]
    assert "dossier" in first
    assert "used_evidence" in first
    assert first["dossier"]["citations"]


def test_apply_research_graph_rejects_unsupported_provider():
    try:
        apply_research_graph(
            ranked_clusters=_ranked_clusters(),
            focus="small business operations",
            research_depth="standard",
            research_top_k=1,
            evidence_pages=2,
            llm_provider="openrouter",
        )
    except ValueError as exc:
        assert "unsupported llm provider" in str(exc)
    else:
        raise AssertionError("expected unsupported provider to raise")
