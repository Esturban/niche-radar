from __future__ import annotations

import os

import requests

from ..models import ProviderResult
from ..utils import is_question_like


def collect_autosuggest(terms: list[str]) -> ProviderResult:
    api_key = os.getenv("BING_AUTOSUGGEST_KEY")
    if not api_key:
        return _collect_google_suggest(terms)

    result = ProviderResult(provider="bing_autosuggest", status="ok")
    headers = {"Ocp-Apim-Subscription-Key": api_key}

    for term in terms:
        try:
            response = requests.get(
                "https://api.bing.microsoft.com/v7.0/suggestions",
                params={"q": term, "mkt": "en-US"},
                headers=headers,
                timeout=10,
            )
            response.raise_for_status()
            payload = response.json()
        except Exception as exc:
            result.status = "degraded"
            result.reason = f"autosuggest degraded: {exc}"
            continue

        suggestions = []
        for group in payload.get("suggestionGroups", []):
            for item in group.get("searchSuggestions", []):
                value = item.get("displayText") or item.get("query")
                if not value:
                    continue
                suggestions.append(
                    {
                        "kind": "autosuggest",
                        "text": value,
                        "question_like": is_question_like(value),
                    }
                )

        if suggestions:
            result.hits[term] = suggestions
            result.metrics[term] = {"autosuggest_count_raw": float(len(suggestions))}

    if not result.hits and result.status == "ok":
        result.status = "unavailable"
        result.reason = "autosuggest returned no suggestions"
    return result


def _collect_google_suggest(terms: list[str]) -> ProviderResult:
    result = ProviderResult(provider="google_suggest", status="ok")
    for term in terms:
        try:
            response = requests.get(
                "https://suggestqueries.google.com/complete/search",
                params={"client": "firefox", "q": term, "hl": "en"},
                timeout=8,
                headers={"User-Agent": "Mozilla/5.0"},
            )
            response.raise_for_status()
            payload = response.json()
        except Exception as exc:
            result.status = "degraded"
            result.reason = f"google suggest degraded: {exc}"
            continue

        suggestions = []
        for value in payload[1] if isinstance(payload, list) and len(payload) > 1 else []:
            if not isinstance(value, str) or not value.strip():
                continue
            suggestions.append(
                {
                    "kind": "autosuggest",
                    "text": value,
                    "question_like": is_question_like(value),
                }
            )
        if suggestions:
            result.hits[term] = suggestions
            result.metrics[term] = {"autosuggest_count_raw": float(len(suggestions))}

    if not result.hits and result.status == "ok":
        result.status = "unavailable"
        result.reason = "google suggest returned no suggestions"
    return result
