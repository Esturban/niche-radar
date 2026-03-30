from __future__ import annotations

import json

from niche_radar.compare import compare_runs


def test_compare_runs_reports_gate_deltas(tmp_path):
    left = tmp_path / "left"
    right = tmp_path / "right"
    left.mkdir()
    right.mkdir()

    (left / "run_meta.json").write_text(
        json.dumps(
            {
                "focus": "small business operations",
                "focus_summary": {"accepted_clusters": [{"cluster": "small business automation"}]},
                "evidence_summary": {"accepted_clusters": [{"cluster": "small business automation"}]},
                "wedge_summary": {"recommended_bet_count": 1},
            }
        ),
        encoding="utf-8",
    )
    (right / "run_meta.json").write_text(
        json.dumps(
            {
                "focus": "shopify ecommerce",
                "focus_summary": {"accepted_clusters": [{"cluster": "shopify ecommerce automation"}]},
                "evidence_summary": {"accepted_clusters": [{"cluster": "shopify ecommerce automation"}]},
                "wedge_summary": {"recommended_bet_count": 1},
            }
        ),
        encoding="utf-8",
    )
    (left / "clusters.json").write_text(
        json.dumps([{"title": "small business automation", "focus_score": 0.8, "evidence_gate": True, "recommended_bet": True}]),
        encoding="utf-8",
    )
    (right / "clusters.json").write_text(
        json.dumps([{"title": "shopify ecommerce automation", "focus_score": 0.9, "evidence_gate": True, "recommended_bet": True}]),
        encoding="utf-8",
    )

    output = compare_runs(left=left, right=right)
    assert "shopify ecommerce automation" in output
    assert "small business automation" in output
    assert "Focus-qualified clusters" in output
