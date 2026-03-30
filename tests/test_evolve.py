from __future__ import annotations

import sys
import types

from niche_radar.evolve import _maybe_llm_expand


class _FakeResponses:
    def __init__(self, output_text: str = "alpha\nbeta", error: Exception | None = None):
        self.output_text = output_text
        self.error = error
        self.calls: list[dict[str, object]] = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        if self.error is not None:
            raise self.error
        return types.SimpleNamespace(output_text=self.output_text)


class _FakeOpenAI:
    def __init__(self, responses: _FakeResponses):
        self.responses = responses


def _install_fake_openai(monkeypatch, responses: _FakeResponses):
    module = types.ModuleType("openai")
    module.OpenAI = lambda api_key: _FakeOpenAI(responses)
    monkeypatch.setitem(sys.modules, "openai", module)


def test_maybe_llm_expand_uses_gpt_54_nano_xhigh_by_default(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.delenv("NICHE_RADAR_OPENAI_MODEL", raising=False)
    monkeypatch.delenv("NICHE_RADAR_OPENAI_REASONING", raising=False)
    responses = _FakeResponses()
    _install_fake_openai(monkeypatch, responses)

    terms = _maybe_llm_expand(base="ops automation", topic="small business operations", keyword_pool=["automation"])

    assert terms == ["alpha", "beta"]
    assert responses.calls == [
        {
            "model": "gpt-5.4-nano",
            "input": "Generate 5 adjacent niche-search phrases, one per line. No numbering, no explanation. Base term: ops automation. Topic: small business operations. Keywords: automation.",
            "max_output_tokens": 200,
            "reasoning": {"effort": "xhigh"},
        }
    ]


def test_maybe_llm_expand_allows_reasoning_override(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("NICHE_RADAR_OPENAI_REASONING", "high")
    responses = _FakeResponses()
    _install_fake_openai(monkeypatch, responses)

    _maybe_llm_expand(base="ops automation", topic="small business operations", keyword_pool=["automation"])

    assert responses.calls[0]["reasoning"] == {"effort": "high"}


def test_maybe_llm_expand_falls_back_to_xhigh_for_invalid_reasoning(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("NICHE_RADAR_OPENAI_REASONING", "turbo")
    responses = _FakeResponses()
    _install_fake_openai(monkeypatch, responses)

    _maybe_llm_expand(base="ops automation", topic="small business operations", keyword_pool=["automation"])

    assert responses.calls[0]["reasoning"] == {"effort": "xhigh"}


def test_maybe_llm_expand_omits_reasoning_for_non_reasoning_models(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("NICHE_RADAR_OPENAI_MODEL", "gpt-4.1-mini")
    responses = _FakeResponses()
    _install_fake_openai(monkeypatch, responses)

    _maybe_llm_expand(base="ops automation", topic="small business operations", keyword_pool=["automation"])

    assert "reasoning" not in responses.calls[0]


def test_maybe_llm_expand_returns_empty_without_api_key(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    assert _maybe_llm_expand(base="ops automation", topic="small business operations", keyword_pool=["automation"]) == []


def test_maybe_llm_expand_returns_empty_when_openai_fails(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    responses = _FakeResponses(error=RuntimeError("boom"))
    _install_fake_openai(monkeypatch, responses)

    assert _maybe_llm_expand(base="ops automation", topic="small business operations", keyword_pool=["automation"]) == []
