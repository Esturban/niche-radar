from __future__ import annotations

import sys
import types

from niche_radar.research_graph.provider import make_research_provider


class _FakeResponses:
    def __init__(self):
        self.calls: list[dict[str, object]] = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return types.SimpleNamespace(output_text="query one\nquery two")


class _FakeOpenAI:
    def __init__(self, responses: _FakeResponses):
        self.responses = responses


def test_openai_research_provider_generates_queries(monkeypatch):
    responses = _FakeResponses()
    module = types.ModuleType("openai")
    module.OpenAI = lambda api_key: _FakeOpenAI(responses)
    monkeypatch.setitem(sys.modules, "openai", module)
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.delenv("NICHE_RADAR_RESEARCH_MODEL", raising=False)
    monkeypatch.delenv("NICHE_RADAR_RESEARCH_REASONING", raising=False)

    provider = make_research_provider("openai")
    queries = provider.generate_follow_up_queries(
        cluster={
            "title": "small business reporting",
            "terms": ["small business reporting", "monthly reporting automation"],
            "questions": ["monthly reporting automation for small business"],
        },
        focus="small business operations",
    )

    assert queries == ["query one", "query two"]
    assert responses.calls
