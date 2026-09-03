"""Tests for the Ollama client (network mocked)."""

import pytest
import requests

from aijobhunter.ai import ollama_client
from aijobhunter.ai.ollama_client import OllamaClient, OllamaError


class _Resp:
    def __init__(self, payload, status=200, text=""):
        self._payload = payload
        self.status_code = status
        self.text = text

    def json(self):
        return self._payload


def test_generate_returns_response_text(settings, monkeypatch):
    monkeypatch.setattr(
        ollama_client.requests, "post", lambda *a, **k: _Resp({"response": "hello"})
    )
    assert OllamaClient(settings).generate("hi") == "hello"


def test_generate_json_parses_response(settings, monkeypatch):
    monkeypatch.setattr(
        ollama_client.requests,
        "post",
        lambda *a, **k: _Resp({"response": '{"skills": ["Python"], "seniority": "senior"}'}),
    )
    result = OllamaClient(settings).generate_json("extract")
    assert result["skills"] == ["Python"]


def test_generate_json_sets_format_json(settings, monkeypatch):
    captured = {}

    def fake_post(url, json=None, timeout=None):
        captured["payload"] = json
        return _Resp({"response": "{}"})

    monkeypatch.setattr(ollama_client.requests, "post", fake_post)
    OllamaClient(settings).generate_json("extract")
    assert captured["payload"]["format"] == "json"
    assert captured["payload"]["model"] == settings.ollama_model
    assert captured["payload"]["stream"] is False


def test_connection_error_raises_helpful(settings, monkeypatch):
    def boom(*a, **k):
        raise requests.exceptions.ConnectionError("refused")

    monkeypatch.setattr(ollama_client.requests, "post", boom)
    with pytest.raises(OllamaError, match="ollama serve"):
        OllamaClient(settings).generate("x")


def test_non_200_raises(settings, monkeypatch):
    monkeypatch.setattr(
        ollama_client.requests, "post", lambda *a, **k: _Resp({}, status=500, text="err")
    )
    with pytest.raises(OllamaError, match="status 500"):
        OllamaClient(settings).generate("x")
