from __future__ import annotations

import json
import os
import re

import requests

from ..models import ProviderResult
from ..utils import is_question_like


def collect_youtube(terms: list[str]) -> ProviderResult:
    api_key = os.getenv("YOUTUBE_API_KEY")
    if not api_key:
        return _collect_youtube_suggest(terms)

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


def _collect_youtube_suggest(terms: list[str]) -> ProviderResult:
    result = ProviderResult(provider="youtube_suggest", status="ok")
    for term in terms:
        try:
            response = requests.get(
                "https://suggestqueries.google.com/complete/search",
                params={"client": "youtube", "ds": "yt", "q": term, "hl": "en"},
                headers={"User-Agent": "Mozilla/5.0"},
                timeout=8,
            )
            response.raise_for_status()
            payload = _parse_youtube_suggest(response.text)
        except Exception as exc:
            result.status = "degraded"
            result.reason = f"youtube suggest degraded: {exc}"
            continue

        hits = []
        for value in payload[1] if isinstance(payload, list) and len(payload) > 1 else []:
            if not isinstance(value, list) or not value:
                continue
            text = value[0].strip()
            if not text:
                continue
            hits.append({"kind": "youtube_suggest", "text": text, "question_like": is_question_like(text)})

        if hits:
            result.hits[term] = hits
            result.metrics[term] = {"youtube_count_raw": float(len(hits))}

    if not result.hits and result.status == "ok":
        result.status = "unavailable"
        result.reason = "youtube suggest returned no results"
    return result


def _parse_youtube_suggest(payload: str) -> list:
    payload = payload.strip()
    if payload.startswith("window.google.ac.h("):
        payload = re.sub(r"^window\.google\.ac\.h\(", "", payload)
        payload = re.sub(r"\)\s*;?\s*$", "", payload)
    return json.loads(payload)
