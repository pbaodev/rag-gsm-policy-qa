"""LLMAdapter (Protocol trong schemas.py) ma Ollama va Claude cung
implement, de retrieve/fallback.py va generate/answer.py khong biet dang
chay model nao - cung nguyen tac "giau sau interface" da lap lai o
Embedder (Buoc 3) va CrossEncoder (Buoc 5). Ca hai goi HTTP truc tiep
bang httpx - khong them LLM SDK rieng (Buoc 0.3: it thu vien, tu viet loi).
"""

from __future__ import annotations

import json
import os
import re

import httpx

_JSON_FENCE_RE = re.compile(r"^```(?:json)?\s*|\s*```$", re.MULTILINE)


def _strip_json_fence(text: str) -> str:
    return _JSON_FENCE_RE.sub("", text).strip()


class OllamaAdapter:
    """Buoc 0: model dev, chay local - khong ton phi, khong gui du lieu
    chinh sach ra ngoai may.

    **Bug/rui ro that (2026-09-22), xem docs/learning/07-*.md:**
    qwen3:4b la reasoning model, mac dinh "nghi" truoc khi tra loi. Voi
    `format: json` (dung cho fallback.generate_json), phan nghi tra ve o
    truong `message.thinking` RIENG, `message.content` van sach (da kiem
    tra that). Nhung goi generate() thuong (final answer, khong format
    json) ton 60-100+ giay va ~900-1500 token nghi cho MOT cau tra loi
    ngan - vi vay timeout mac dinh nang len 300s (120s tung bi timeout
    that khi chay full pipeline tren du lieu that). Da thu `"think": false`
    de tat nghi - KHONG hoat dong dung tren ban Ollama dang dung: toan bo
    noi dung nghi bi don thang vao `message.content` kem the `</think>`
    tho, con lau hon (101s) - vi vay KHONG dung think=false, chi tang
    timeout va chap nhan do tre."""

    def __init__(
        self,
        model: str,
        *,
        base_url: str = "http://localhost:11434",
        temperature: float = 0.15,
        timeout: float = 300.0,
    ) -> None:
        self._model = model
        self._base_url = base_url.rstrip("/")
        self._temperature = temperature
        self._timeout = timeout

    def _chat(self, system: str, user: str, *, json_mode: bool) -> str:
        payload = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "stream": False,
            "options": {"temperature": self._temperature},
        }
        if json_mode:
            payload["format"] = "json"
        resp = httpx.post(f"{self._base_url}/api/chat", json=payload, timeout=self._timeout)
        resp.raise_for_status()
        return resp.json()["message"]["content"]

    def generate(self, system: str, user: str) -> str:
        return self._chat(system, user, json_mode=False)

    def generate_json(self, system: str, user: str, schema_hint: str) -> dict:
        full_system = f"{system}\n\nTra ve DUNG mot JSON object khop schema sau, khong them chu nao khac:\n{schema_hint}"
        raw = self._chat(full_system, user, json_mode=True)
        return json.loads(_strip_json_fence(raw))


class ClaudeAdapter:
    """Buoc 0: model khi can chat luong hon qwen3:4b. Chua chay that (khong
    co ANTHROPIC_API_KEY trong moi truong dev) - xem CLAUDE.md known loose
    ends. Claude API khong co tham so ep JSON cung nhu Ollama, nen
    generate_json them huong dan vao system prompt roi tu parse."""

    _API_URL = "https://api.anthropic.com/v1/messages"
    _API_VERSION = "2023-06-01"

    def __init__(self, model: str, *, api_key: str | None = None, temperature: float = 0.15, max_tokens: int = 1024) -> None:
        self._model = model
        self._api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        if not self._api_key:
            raise RuntimeError("ANTHROPIC_API_KEY khong duoc dat trong moi truong")
        self._temperature = temperature
        self._max_tokens = max_tokens

    def _call(self, system: str, user: str) -> str:
        headers = {
            "x-api-key": self._api_key,
            "anthropic-version": self._API_VERSION,
            "content-type": "application/json",
        }
        payload = {
            "model": self._model,
            "system": system,
            "messages": [{"role": "user", "content": user}],
            "max_tokens": self._max_tokens,
            "temperature": self._temperature,
        }
        resp = httpx.post(self._API_URL, headers=headers, json=payload, timeout=120.0)
        resp.raise_for_status()
        return resp.json()["content"][0]["text"]

    def generate(self, system: str, user: str) -> str:
        return self._call(system, user)

    def generate_json(self, system: str, user: str, schema_hint: str) -> dict:
        full_system = (
            f"{system}\n\nTra ve DUNG mot JSON object khop schema sau, khong them chu nao khac, "
            f"khong dung markdown fence:\n{schema_hint}"
        )
        raw = self._call(full_system, user)
        return json.loads(_strip_json_fence(raw))


def build_llm_adapter(model_spec: str, *, temperature: float = 0.15) -> OllamaAdapter | ClaudeAdapter:
    """model_spec dang 'provider:model' nhu trong config/default.toml,
    vi du 'ollama:qwen3:4b', 'claude:claude-sonnet-5'."""
    provider, sep, model = model_spec.partition(":")
    if not sep:
        raise ValueError(f"model_spec '{model_spec}' phai co dang 'provider:model'")
    if provider == "ollama":
        return OllamaAdapter(model, temperature=temperature)
    if provider == "claude":
        return ClaudeAdapter(model, temperature=temperature)
    raise ValueError(f"Khong nhan dien provider '{provider}' trong model_spec '{model_spec}'")
