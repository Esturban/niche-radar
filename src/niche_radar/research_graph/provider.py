from __future__ import annotations

import os

from ..utils import dedupe_preserve_order

DEFAULT_PROVIDER = "openai"
DEFAULT_MODEL = "gpt-5.4-nano"
DEFAULT_REASONING = "medium"
ALLOWED_REASONING = {"none", "minimal", "low", "medium", "high", "xhigh"}


class ResearchProvider:
    def generate_follow_up_queries(self, *, cluster: dict, focus: str) -> list[str]:
        raise NotImplementedError


class NullResearchProvider(ResearchProvider):
    def generate_follow_up_queries(self, *, cluster: dict, focus: str) -> list[str]:
        return []


class OpenAIResearchProvider(ResearchProvider):
    def __init__(self) -> None:
        self._api_key = os.getenv("OPENAI_API_KEY", "").strip()

    def generate_follow_up_queries(self, *, cluster: dict, focus: str) -> list[str]:
        if not self._api_key:
            return []

        try:
            from openai import OpenAI
        except ImportError:
            return []

        title = cluster.get("title") or cluster.get("title_seed") or ""
        terms = ", ".join(cluster.get("terms", [])[:6])
        questions = ", ".join(cluster.get("questions", [])[:4])
        prompt = (
            "Generate up to 3 short search queries to validate niche demand and search behavior. "
            "Use one query per line. No numbering or explanation. "
            f"Niche: {title}. Focus: {focus}. Existing terms: {terms}. Existing questions: {questions}."
        )
        request: dict[str, object] = {
            "model": _resolve_model(),
            "input": prompt,
            "max_output_tokens": 160,
        }
        if _supports_reasoning(request["model"]):
            request["reasoning"] = {"effort": _resolve_reasoning()}

        try:
            client = OpenAI(api_key=self._api_key)
            response = client.responses.create(**request)
        except Exception:
            return []

        text = getattr(response, "output_text", "") or ""
        return dedupe_preserve_order(
            [line.strip("- ").strip() for line in text.splitlines() if line.strip()]
        )


def make_research_provider(name: str) -> ResearchProvider:
    normalized = (name or DEFAULT_PROVIDER).strip().lower()
    if normalized == "openai":
        return OpenAIResearchProvider()
    raise ValueError(f"unsupported llm provider: {name}")


def _resolve_model() -> str:
    model = os.getenv("NICHE_RADAR_RESEARCH_MODEL", "").strip()
    if model:
        return model
    shared = os.getenv("NICHE_RADAR_OPENAI_MODEL", "").strip()
    return shared or DEFAULT_MODEL


def _resolve_reasoning() -> str:
    value = os.getenv("NICHE_RADAR_RESEARCH_REASONING", "").strip().lower()
    if value in ALLOWED_REASONING:
        return value
    shared = os.getenv("NICHE_RADAR_OPENAI_REASONING", "").strip().lower()
    if shared in ALLOWED_REASONING:
        return shared
    return DEFAULT_REASONING


def _supports_reasoning(model: object) -> bool:
    normalized = str(model).strip().lower()
    return normalized.startswith(("gpt-5", "o"))
