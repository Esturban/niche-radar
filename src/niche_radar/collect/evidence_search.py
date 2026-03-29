from __future__ import annotations

import html
import os
import re
from datetime import datetime, timezone
from urllib.parse import parse_qs, unquote, urlparse

import requests

from ..ingest import fetch_page
from ..utils import clamp01, content_tokens, safe_mean

DUCKDUCKGO_HTML_ENDPOINT = "https://html.duckduckgo.com/html/"
YOU_SEARCH_ENDPOINT = "https://ydc-index.io/v1/search"
REQUEST_TIMEOUT = 12
SEARCH_USER_AGENT = "Mozilla/5.0"
SNIPPET_WINDOW = 320
PROBLEM_MARKERS = {
    "automation",
    "consultant",
    "efficiency",
    "help",
    "how",
    "integration",
    "operations",
    "process",
    "reporting",
    "service",
    "software",
    "system",
    "template",
    "tool",
    "workflow",
}


def collect_evidence_search(clusters: list[dict], focus: str, evidence_pages: int = 3) -> dict[str, dict]:
    if not clusters or evidence_pages <= 0:
        return {}

    if os.getenv("YOU_API_KEY"):
        return _collect_you_evidence(clusters=clusters, focus=focus, evidence_pages=evidence_pages)
    return _collect_duckduckgo_evidence(clusters=clusters, focus=focus, evidence_pages=evidence_pages)


def flatten_evidence(evidence_by_cluster: dict[str, dict]) -> list[dict]:
    items: list[dict] = []
    for cluster_id, payload in evidence_by_cluster.items():
        for item in payload.get("items", []):
            items.append({"cluster_id": cluster_id, **item})
    return items


def _collect_you_evidence(clusters: list[dict], focus: str, evidence_pages: int) -> dict[str, dict]:
    api_key = os.getenv("YOU_API_KEY")
    headers = {"X-API-Key": api_key, "User-Agent": SEARCH_USER_AGENT}
    output: dict[str, dict] = {}

    for cluster in clusters:
        query = _build_query(cluster["title_seed"], focus)
        payload = {
            "provider": "you_search",
            "query": query,
            "items": [],
            "search_results_examined": 0,
            "citation_count": 0,
            "snippet_quality_raw": 0.0,
            "recency_support_raw": 0.0,
        }
        try:
            response = requests.get(
                YOU_SEARCH_ENDPOINT,
                params={
                    "query": query,
                    "count": max(evidence_pages, 3),
                    "freshness": "year",
                },
                headers=headers,
                timeout=REQUEST_TIMEOUT,
            )
            response.raise_for_status()
            data = response.json()
        except Exception as exc:
            payload["error"] = f"you search degraded: {exc}"
            output[cluster["cluster_id"]] = payload
            continue

        raw_results = []
        results = data.get("results") or {}
        for section in ("web", "news"):
            raw_results.extend(results.get(section) or [])
        payload["search_results_examined"] = len(raw_results)

        evidence_items = _build_evidence_items(
            provider="you_search",
            query=query,
            raw_results=raw_results,
            evidence_pages=evidence_pages,
        )
        payload.update(_summarize_evidence(evidence_items))
        output[cluster["cluster_id"]] = payload

    return output


def _collect_duckduckgo_evidence(clusters: list[dict], focus: str, evidence_pages: int) -> dict[str, dict]:
    output: dict[str, dict] = {}

    for cluster in clusters:
        query = _build_query(cluster["title_seed"], focus)
        payload = {
            "provider": "duckduckgo_html",
            "query": query,
            "items": [],
            "search_results_examined": 0,
            "citation_count": 0,
            "snippet_quality_raw": 0.0,
            "recency_support_raw": 0.0,
        }
        try:
            response = requests.get(
                DUCKDUCKGO_HTML_ENDPOINT,
                params={"q": query},
                headers={"User-Agent": SEARCH_USER_AGENT},
                timeout=REQUEST_TIMEOUT,
            )
            response.raise_for_status()
        except Exception as exc:
            payload["error"] = f"duckduckgo search degraded: {exc}"
            output[cluster["cluster_id"]] = payload
            continue

        raw_results = _parse_duckduckgo_results(response.text)
        payload["search_results_examined"] = len(raw_results)

        evidence_items = _build_evidence_items(
            provider="duckduckgo_html",
            query=query,
            raw_results=raw_results,
            evidence_pages=evidence_pages,
        )
        payload.update(_summarize_evidence(evidence_items))
        output[cluster["cluster_id"]] = payload

    return output


def _summarize_evidence(evidence_items: list[dict]) -> dict:
    return {
        "items": evidence_items,
        "citation_count": len(evidence_items),
        "snippet_quality_raw": safe_mean(item.get("quality_score", 0.0) for item in evidence_items),
        "recency_support_raw": safe_mean(item.get("recency_score", 0.0) for item in evidence_items if item.get("recency_score") is not None),
    }


def _build_evidence_items(provider: str, query: str, raw_results: list[dict], evidence_pages: int) -> list[dict]:
    query_tokens = set(content_tokens(query))
    evidence_items: list[dict] = []

    for result in raw_results:
        if len(evidence_items) >= evidence_pages:
            break

        url = (result.get("url") or "").strip()
        title = (result.get("title") or "").strip()
        if not url or not title:
            continue

        page = fetch_page(url)
        snippet = ""
        if page and page.get("text"):
            snippet = _extract_relevant_snippet(page["text"], query_tokens)
        if not snippet:
            snippet = _extract_relevant_snippet(" ".join(result.get("snippets") or []) or result.get("description") or "", query_tokens)
        if not snippet:
            continue

        matched_terms = sorted(set(content_tokens(snippet)) & query_tokens)
        quality_score = _score_snippet_quality(snippet=snippet, matched_terms=matched_terms, query_tokens=query_tokens)
        evidence_items.append(
            {
                "provider": provider,
                "query": query,
                "url": url,
                "title": title,
                "snippet": snippet,
                "matched_terms": matched_terms,
                "published_at": result.get("page_age"),
                "recency_score": _recency_score(result.get("page_age")),
                "quality_score": round(quality_score, 4),
            }
        )

    return evidence_items


def _build_query(title: str, focus: str) -> str:
    if not focus:
        return title
    title_tokens = set(content_tokens(title))
    focus_tokens = set(content_tokens(focus))
    if title_tokens & focus_tokens:
        return title
    return f"{title} {focus}".strip()


def _extract_relevant_snippet(text: str, query_tokens: set[str]) -> str:
    normalized = " ".join(text.split())
    if not normalized:
        return ""
    if not query_tokens:
        return normalized[:SNIPPET_WINDOW].strip()

    lowered = normalized.lower()
    hit_index = min((lowered.find(token) for token in query_tokens if lowered.find(token) >= 0), default=-1)
    if hit_index < 0:
        return normalized[:SNIPPET_WINDOW].strip()

    start = max(0, hit_index - 120)
    end = min(len(normalized), hit_index + SNIPPET_WINDOW)
    snippet = normalized[start:end].strip()
    if start > 0:
        snippet = f"... {snippet}"
    if end < len(normalized):
        snippet = f"{snippet} ..."
    return snippet


def _score_snippet_quality(snippet: str, matched_terms: list[str], query_tokens: set[str]) -> float:
    overlap_score = len(matched_terms) / max(1, len(query_tokens))
    problem_score = 1.0 if set(content_tokens(snippet)) & PROBLEM_MARKERS else 0.0
    return clamp01((overlap_score * 0.75) + (problem_score * 0.25))


def _recency_score(value: str | None) -> float | None:
    if not value:
        return None
    try:
        published_at = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if published_at.tzinfo is None:
        published_at = published_at.replace(tzinfo=timezone.utc)
    age_days = max(0.0, (datetime.now(timezone.utc) - published_at).total_seconds() / 86400)
    if age_days <= 30:
        return 1.0
    if age_days <= 90:
        return 0.75
    if age_days <= 180:
        return 0.5
    if age_days <= 365:
        return 0.25
    return 0.0


def _parse_duckduckgo_results(payload: str) -> list[dict]:
    pattern = re.compile(
        r'<h2 class="result__title">.*?<a[^>]*class="result__a" href="(?P<href>[^"]+)".*?>(?P<title>.*?)</a>.*?(?:<a class="result__snippet"[^>]*>(?P<snippet>.*?)</a>)?',
        re.S,
    )
    results: list[dict] = []
    for match in pattern.finditer(payload):
        title = _strip_tags(match.group("title"))
        snippet = _strip_tags(match.group("snippet") or "")
        url = _unwrap_duckduckgo_redirect(match.group("href"))
        if not title or not url:
            continue
        results.append(
            {
                "url": url,
                "title": title,
                "description": snippet,
                "snippets": [snippet] if snippet else [],
            }
        )
    return results


def _strip_tags(value: str) -> str:
    return html.unescape(re.sub(r"<[^>]+>", "", value or "")).strip()


def _unwrap_duckduckgo_redirect(url: str) -> str:
    url = html.unescape(url)
    if url.startswith("//"):
        url = f"https:{url}"
    parsed = urlparse(url)
    if parsed.netloc.endswith("duckduckgo.com"):
        query = parse_qs(parsed.query)
        if "uddg" in query and query["uddg"]:
            return unquote(query["uddg"][0])
    return url
