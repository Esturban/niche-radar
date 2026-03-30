from __future__ import annotations

import json
from pathlib import Path

from niche_radar.models import ProviderResult, RunConfig
from niche_radar.pipeline import discover
from niche_radar.cluster import cluster_terms
from niche_radar.collect.youtube import _parse_youtube_suggest


def _fake_trends(terms, topic, geo="US"):
    metrics = {}
    hits = {}
    for index, term in enumerate(terms):
        metrics[term] = {
            "trend_strength_raw": 0.4 + (index / max(1, len(terms))) * 0.6,
            "trend_velocity_raw": 0.1 + (index / max(1, len(terms))) * 0.4,
            "trend_calibrated": True,
        }
        hits[term] = [{"kind": "related_query", "text": f"{term} tutorial"}]
    return ProviderResult(provider="google_trends", status="ok", metrics=metrics, hits=hits)


def _fake_autosuggest(terms):
    return ProviderResult(
        provider="bing_autosuggest",
        status="ok",
        metrics={term: {"autosuggest_count_raw": 3.0} for term in terms},
        hits={
            term: [
                {"kind": "autosuggest", "text": f"how to {term}", "question_like": True},
                {"kind": "autosuggest", "text": f"{term} template", "question_like": False},
            ]
            for term in terms
        },
    )


def _fake_youtube(terms):
    return ProviderResult(
        provider="youtube",
        status="ok",
        metrics={term: {"youtube_count_raw": 2.0} for term in terms},
        hits={term: [{"kind": "youtube", "text": f"How to use {term}", "question_like": True}] for term in terms},
    )


def _fake_evidence(clusters, focus, evidence_pages):
    output = {}
    for cluster in clusters:
        output[cluster["cluster_id"]] = {
            "provider": "test_evidence",
            "query": cluster["title_seed"],
            "items": [
                {
                    "provider": "test_evidence",
                    "query": cluster["title_seed"],
                    "url": f"https://example.com/{cluster['cluster_id'].replace(' ', '-')}",
                    "title": f"{cluster['title_seed']} guide",
                    "snippet": f"{cluster['title_seed']} automation workflow evidence",
                    "matched_terms": ["automation", "workflow"],
                    "published_at": "2026-03-01T00:00:00+00:00",
                    "recency_score": 1.0,
                    "quality_score": 0.9,
                }
            ],
            "citation_count": 1,
            "snippet_quality_raw": 0.9,
            "recency_support_raw": 1.0,
        }
    return output


def test_discover_writes_expected_artifacts(monkeypatch, tmp_path):
    monkeypatch.setattr("niche_radar.pipeline.collect_trends", _fake_trends)
    monkeypatch.setattr("niche_radar.pipeline.collect_autosuggest", _fake_autosuggest)
    monkeypatch.setattr("niche_radar.pipeline.collect_youtube", _fake_youtube)
    monkeypatch.setattr("niche_radar.pipeline.collect_evidence_search", _fake_evidence)
    monkeypatch.setattr("niche_radar.research_graph.engine.collect_evidence_search", _fake_evidence)

    config = RunConfig(
        resume_path=Path("tests/fixtures/resume.md"),
        site_url=None,
        focus="small business operations",
        outdir=tmp_path / "run",
        top_niches=4,
    )
    result = discover(config)

    assert result["cluster_count"] > 0
    for name in [
        "report.md",
        "clusters.json",
        "used_evidence.json",
        "run_meta.json",
    ]:
        assert (tmp_path / "run" / name).exists()
    for name in [
        "evidence.json",
        "terms.csv",
        "question_graph.json",
        "trends.csv",
        "provider_hits.json",
        "research_trace.json",
    ]:
        assert not (tmp_path / "run" / name).exists()

    report = (tmp_path / "run" / "report.md").read_text(encoding="utf-8")
    assert "## Recommended bets" in report
    clusters = json.loads((tmp_path / "run" / "clusters.json").read_text(encoding="utf-8"))
    assert clusters
    assert "profile_fit_score" in clusters[0]
    assert "evidence_strength" in clusters[0]
    assert "micro_wedges" in clusters[0]
    assert "dossier" in clusters[0]
    assert "research_score" in clusters[0]
    run_meta = json.loads((tmp_path / "run" / "run_meta.json").read_text(encoding="utf-8"))
    assert "wedge_summary" in run_meta
    assert run_meta["wedge_summary"]["specificity_outcome"] in {"recommended_bets_found", "not_specific_enough"}
    assert run_meta["research_summary"]["depth"] == "standard"


def test_discover_persist_trace_writes_debug_artifacts(monkeypatch, tmp_path):
    monkeypatch.setattr("niche_radar.pipeline.collect_trends", _fake_trends)
    monkeypatch.setattr("niche_radar.pipeline.collect_autosuggest", _fake_autosuggest)
    monkeypatch.setattr("niche_radar.pipeline.collect_youtube", _fake_youtube)
    monkeypatch.setattr("niche_radar.pipeline.collect_evidence_search", _fake_evidence)
    monkeypatch.setattr("niche_radar.research_graph.engine.collect_evidence_search", _fake_evidence)

    config = RunConfig(
        resume_path=Path("tests/fixtures/resume.md"),
        site_url=None,
        focus="small business operations",
        outdir=tmp_path / "run",
        top_niches=4,
        persist_trace=True,
    )
    discover(config)

    for name in [
        "evidence.json",
        "terms.csv",
        "question_graph.json",
        "trends.csv",
        "provider_hits.json",
        "research_trace.json",
    ]:
        assert (tmp_path / "run" / name).exists()


def test_discover_research_off_skips_dossier_stage(monkeypatch, tmp_path):
    monkeypatch.setattr("niche_radar.pipeline.collect_trends", _fake_trends)
    monkeypatch.setattr("niche_radar.pipeline.collect_autosuggest", _fake_autosuggest)
    monkeypatch.setattr("niche_radar.pipeline.collect_youtube", _fake_youtube)
    monkeypatch.setattr("niche_radar.pipeline.collect_evidence_search", _fake_evidence)

    config = RunConfig(
        resume_path=Path("tests/fixtures/resume.md"),
        site_url=None,
        focus="small business operations",
        outdir=tmp_path / "run",
        top_niches=4,
        research_depth="off",
    )
    discover(config)

    clusters = json.loads((tmp_path / "run" / "clusters.json").read_text(encoding="utf-8"))
    assert clusters
    assert "dossier" not in clusters[0]
    run_meta = json.loads((tmp_path / "run" / "run_meta.json").read_text(encoding="utf-8"))
    assert run_meta["research_summary"]["depth"] == "off"


def test_insufficient_signal_creates_report(monkeypatch, tmp_path):
    empty = ProviderResult(provider="google_trends", status="unavailable", reason="no provider")
    monkeypatch.setattr("niche_radar.pipeline.collect_trends", lambda terms, topic, geo="US": empty)
    monkeypatch.setattr("niche_radar.pipeline.collect_autosuggest", lambda terms: ProviderResult(provider="bing_autosuggest", status="unavailable", reason="no key"))
    monkeypatch.setattr("niche_radar.pipeline.collect_youtube", lambda terms: ProviderResult(provider="youtube", status="unavailable", reason="no key"))

    config = RunConfig(
        resume_path=Path("tests/fixtures/resume.md"),
        site_url=None,
        focus="operations automation",
        outdir=tmp_path / "run",
        top_niches=4,
    )
    result = discover(config)
    assert result["insufficient_signal"] is True
    report = (tmp_path / "run" / "report.md").read_text(encoding="utf-8")
    assert "Insufficient signal" in report
    assert (tmp_path / "run" / "used_evidence.json").exists()


def test_cluster_terms_split_operator_signals():
    clusters = cluster_terms(
        {
            "small business automation": {
                "term": "small business automation",
                "generation": 0,
                "lineage_root": "small business automation",
                "hits": [],
            },
            "small business dashboard": {
                "term": "small business dashboard",
                "generation": 0,
                "lineage_root": "small business dashboard",
                "hits": [],
            },
        }
    )
    titles = {cluster["title_seed"] for cluster in clusters}
    assert "small business automation" in titles
    assert "small business dashboard" in titles


def test_parse_youtube_suggest_wrapper():
    payload = 'window.google.ac.h(["small business automation",[["small business automation",0,[512]],["small business automation software",0,[22,30]]],{"k":1}])'
    parsed = _parse_youtube_suggest(payload)
    assert parsed[0] == "small business automation"
    assert parsed[1][1][0] == "small business automation software"
