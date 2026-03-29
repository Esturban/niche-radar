from niche_radar.calibrate import normalize_trend_batch


def test_normalize_trend_batch_uses_anchors():
    normalized, calibrated = normalize_trend_batch(
        series_by_term={
            "small business": [10, 10, 10],
            "how to start a business": [10, 10, 10],
            "ops automation": [20, 30, 40],
        },
        anchor_terms=["small business", "how to start a business"],
    )
    assert calibrated is True
    assert normalized["ops automation"]["trend_strength_raw"] > 0
    assert normalized["ops automation"]["trend_velocity_raw"] > 0


def test_normalize_trend_batch_fails_without_anchor_signal():
    normalized, calibrated = normalize_trend_batch(
        series_by_term={
            "small business": [0, 0, 0],
            "how to start a business": [0, 0, 0],
            "ops automation": [20, 30, 40],
        },
        anchor_terms=["small business", "how to start a business"],
    )
    assert calibrated is False
    assert normalized == {}

