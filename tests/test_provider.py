"""Tests for the LLM provider factory."""

from aijobhunter.ai.ollama_client import OllamaClient
from aijobhunter.ai.provider import build_llm_client


def test_build_llm_client_returns_ollama(settings):
    assert isinstance(build_llm_client(settings), OllamaClient)
