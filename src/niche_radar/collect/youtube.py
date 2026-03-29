from __future__ import annotations

import os

import requests

from ..models import ProviderResult
from ..utils import is_question_like


def collect_youtube(terms: list[str]) -> ProviderResult:
    api_key = os.getenv("YOUTUBE_API_KEY")
    if not api_key:
        return ProviderResult(
            provider="youtube",
            status="unavailable",
            reason="YOUTUBE_API_KEY is not set",
        )

    result = ProviderResult(provider="youtube", status="ok")
    endpoint = "https://www.googleapis.com/youtube/v3/search"

    for term in terms:
        try:
            response = requests.get(
                endpoint,
                params={
                    "part": "snippet",
                    "type": "video",
                    "maxResults": 5,
                    "q": f"how to {term}",
                    "key": api_key,
                },
                timeout=10,
            )
            response.raise_for_status()
            payload = response.json()
        except Exception as exc:
            result.status = "degraded"
            result.reason = f"youtube degraded: {exc}"
            continue

        hits = []
        for item in payload.get("items", []):
            snippet = item.get("snippet", {})
            title = snippet.get("title", "").strip()
            if title:
                hits.append(
                    {
                        "kind": "youtube",
                        "text": title,
                        "channel": snippet.get("channelTitle"),
                        "question_like": is_question_like(title),
                    }
                )
        if hits:
            result.hits[term] = hits
            result.metrics[term] = {"youtube_count_raw": float(len(hits))}

    if not result.hits and result.status == "ok":
        result.status = "unavailable"
        result.reason = "youtube returned no results"
    return result

