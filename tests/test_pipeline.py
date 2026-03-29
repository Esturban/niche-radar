from __future__ import annotations

import json
from pathlib import Path

from niche_radar.models import ProviderResult, RunConfig
from niche_radar.pipeline import discover


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


def test_discover_writes_expected_artifacts(monkeypatch, tmp_path):
    monkeypatch.setattr("niche_radar.pipeline.collect_trends", _fake_trends)
    monkeypatch.setattr("niche_radar.pipeline.collect_autosuggest", _fake_autosuggest)
    monkeypatch.setattr("niche_radar.pipeline.collect_youtube", _fake_youtube)

    config = RunConfig(
        resume_path=Path("tests/fixtures/resume.md"),
        topic="small business operations",
        outdir=tmp_path / "run",
        max_clusters=4,
    )
    result = discover(config)

    assert result["cluster_count"] > 0
    for name in [
        "report.md",
        "clusters.json",
        "terms.csv",
        "question_graph.json",
        "trends.csv",
        "provider_hits.json",
        "run_meta.json",
    ]:
        assert (tmp_path / "run" / name).exists()

    report = (tmp_path / "run" / "report.md").read_text(encoding="utf-8")
    assert "validated demand" in report
    clusters = json.loads((tmp_path / "run" / "clusters.json").read_text(encoding="utf-8"))
    assert clusters
    assert "profile_fit_score" in clusters[0]


def test_insufficient_signal_creates_report(monkeypatch, tmp_path):
    empty = ProviderResult(provider="google_trends", status="unavailable", reason="no provider")
    monkeypatch.setattr("niche_radar.pipeline.collect_trends", lambda terms, topic, geo="US": empty)
    monkeypatch.setattr("niche_radar.pipeline.collect_autosuggest", lambda terms: ProviderResult(provider="bing_autosuggest", status="unavailable", reason="no key"))
    monkeypatch.setattr("niche_radar.pipeline.collect_youtube", lambda terms: ProviderResult(provider="youtube", status="unavailable", reason="no key"))

    config = RunConfig(
        resume_path=Path("tests/fixtures/resume.md"),
        topic="operations automation",
        outdir=tmp_path / "run",
        max_clusters=4,
    )
    result = discover(config)
    assert result["insufficient_signal"] is True
    report = (tmp_path / "run" / "report.md").read_text(encoding="utf-8")
    assert "Insufficient signal" in report

