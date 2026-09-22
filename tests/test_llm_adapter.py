"""Test rag_gsm.generate.llm_adapter - chi test logic thuan tuy (factory
routing, strip JSON fence, thieu API key). Goi that toi Ollama/Claude
khong test o day (can server/network that) - xem generate/run.py de test
thu cong tren du lieu that."""

from __future__ import annotations

import pytest

from rag_gsm.generate.llm_adapter import ClaudeAdapter, OllamaAdapter, _strip_json_fence, build_llm_adapter


def test_build_llm_adapter_routes_ollama():
    adapter = build_llm_adapter("ollama:qwen3:4b")
    assert isinstance(adapter, OllamaAdapter)


def test_build_llm_adapter_routes_claude(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "fake-key")
    adapter = build_llm_adapter("claude:claude-sonnet-5")
    assert isinstance(adapter, ClaudeAdapter)


def test_build_llm_adapter_rejects_unknown_provider():
    with pytest.raises(ValueError):
        build_llm_adapter("gpt:whatever")


def test_build_llm_adapter_rejects_missing_colon():
    with pytest.raises(ValueError):
        build_llm_adapter("qwen3")


def test_claude_adapter_requires_api_key(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    with pytest.raises(RuntimeError):
        ClaudeAdapter("claude-sonnet-5")


def test_strip_json_fence_removes_markdown_fence():
    raw = '```json\n{"a": 1}\n```'
    assert _strip_json_fence(raw) == '{"a": 1}'


def test_strip_json_fence_noop_on_plain_json():
    raw = '{"a": 1}'
    assert _strip_json_fence(raw) == '{"a": 1}'
