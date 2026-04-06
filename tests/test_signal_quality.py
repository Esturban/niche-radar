from __future__ import annotations

from niche_radar.signal_quality import (
    classify_signal_text,
    founder_core_tokens,
    is_generic_parent_phrase,
    is_packaging_heavy,
    summarize_signal_groups,
)


def test_classify_signal_text_filters_noise_and_packaging():
    assert classify_signal_text("shopify operations automation software engineer") == "noise"
    assert classify_signal_text("shopify operations automation consultants") == "supporting_packaging"
    assert classify_signal_text("shopify exception reporting export workflow") == "trusted_workaround"


def test_founder_core_tokens_strip_generic_and_packaging_words():
    assert founder_core_tokens("shopify operations automation dashboard templates") == ["dashboard"]
    assert founder_core_tokens("shopify exception reporting export workflow") == ["exception", "reporting", "export"]


def test_generic_parent_and_packaging_detection_stays_strict():
    assert is_generic_parent_phrase("shopify operations automation") is True
    assert is_generic_parent_phrase("shopify exception reporting") is False
    assert is_packaging_heavy("reporting templates for operators") is True


def test_summarize_signal_groups_separates_trusted_and_noise_terms():
    summary = summarize_signal_groups(
        terms=["shopify exception reporting", "shopify operations automation consultants"],
        questions=["shopify exception reporting export workflow", "shopify operations automation software engineer"],
        related_terms=["shopify exception reporting spreadsheet", "shopify operations automation template"],
    )

    assert "shopify exception reporting" in summary["trusted_terms"]
    assert "shopify exception reporting export workflow" in summary["trusted_questions"]
    assert "shopify operations automation consultants" in summary["packaging_terms"]
    assert "shopify operations automation software engineer" in summary["noise_terms"]
    assert summary["trusted_signal_score"] > 0
