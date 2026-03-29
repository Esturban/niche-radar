from __future__ import annotations

from . import __name__  # noqa: F401
from ..calibrate import normalize_trend_batch
from ..models import ProviderResult
from ..utils import chunks, dedupe_preserve_order

DEFAULT_ANCHORS = ["small business", "how to start a business"]


def collect_trends(terms: list[str], topic: str, geo: str = "US") -> ProviderResult:
    try:
        from pytrends.request import TrendReq
    except ImportError:
        return ProviderResult(
            provider="google_trends",
            status="unavailable",
            reason="pytrends is not installed",
        )

    candidates = [term for term in dedupe_preserve_order(terms) if term.lower() not in {anchor.lower() for anchor in DEFAULT_ANCHORS}]
    if not candidates:
        return ProviderResult(provider="google_trends", status="unavailable", reason="no candidate terms")

    trend = TrendReq(
        hl="en-US",
        tz=360,
        timeout=(4, 12),
        retries=0,
        backoff_factor=0,
    )
    result = ProviderResult(provider="google_trends", status="ok", meta={"anchors": DEFAULT_ANCHORS, "topic": topic, "geo": geo})

    for batch in chunks(candidates, 3):
        keywords = batch + DEFAULT_ANCHORS
        try:
            trend.build_payload(keywords, timeframe="today 12-m", geo=geo)
            frame = trend.interest_over_time()
        except Exception as exc:
            result.status = "degraded"
            result.reason = f"trend collection degraded: {exc}"
            continue

        if getattr(frame, "empty", True):
            result.status = "degraded"
            result.reason = "google trends returned no data"
            continue

        series_by_term: dict[str, list[float]] = {}
        for term in keywords:
            if term not in frame.columns:
                continue
            values = [float(value) for value in frame[term].tolist()]
            series_by_term[term] = values

        normalized, calibrated = normalize_trend_batch(series_by_term=series_by_term, anchor_terms=DEFAULT_ANCHORS)
        for term, metrics in normalized.items():
            result.metrics.setdefault(term, {}).update(metrics)
            result.metrics[term]["trend_calibrated"] = calibrated

        try:
            related_queries = trend.related_queries() or {}
        except Exception:
            related_queries = {}

        for term in batch:
            term_queries = related_queries.get(term) or {}
            hits: list[dict] = []
            for label in ("top", "rising"):
                table = term_queries.get(label)
                if table is None:
                    continue
                for _, row in table.head(5).iterrows():
                    query = str(row.get("query", "")).strip()
                    if query:
                        hits.append({"kind": "related_query", "label": label, "text": query})
            if hits:
                result.hits.setdefault(term, []).extend(hits)

    if not result.metrics and not result.hits and result.status == "ok":
        result.status = "unavailable"
        result.reason = "google trends returned no usable metrics"
    return result
