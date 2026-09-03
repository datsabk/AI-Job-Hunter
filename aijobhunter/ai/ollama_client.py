"""Ollama client — local LLM backend (default provider).

Talks to a local Ollama server (default http://localhost:11434) using the
``/api/generate`` endpoint with ``stream: false``. For ``generate_json`` it sets
Ollama's ``format: "json"`` so the model is constrained to emit valid JSON.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

import requests

from ..config import Settings
from .json_utils import extract_json_object

logger = logging.getLogger(__name__)


class OllamaError(Exception):
    """Raised on any Ollama call failure."""


class OllamaClient:
    """Minimal client for a local Ollama model (e.g. llama3)."""

    def __init__(self, settings: Settings, timeout: int = 120) -> None:
        self._base_url = settings.ollama_base_url.rstrip("/")
        self._model = settings.ollama_model
        self._temperature = settings.llm_temperature
        self._timeout = timeout

    def generate(self, prompt: str, max_tokens: Optional[int] = None) -> str:
        return self._call(prompt, max_tokens=max_tokens, json_mode=False)

    def generate_json(self, prompt: str, max_tokens: Optional[int] = None) -> dict[str, Any]:
        text = self._call(prompt, max_tokens=max_tokens, json_mode=True)
        try:
            return extract_json_object(text)
        except ValueError as exc:
            raise OllamaError(f"Could not parse JSON from Ollama response: {exc}") from exc

    def _call(self, prompt: str, max_tokens: Optional[int], json_mode: bool) -> str:
        options: dict[str, Any] = {"temperature": self._temperature}
        if max_tokens:
            options["num_predict"] = max_tokens

        payload: dict[str, Any] = {
            "model": self._model,
            "prompt": prompt,
            "stream": False,
            "options": options,
        }
        if json_mode:
            payload["format"] = "json"

        url = f"{self._base_url}/api/generate"
        logger.info("Calling Ollama url=%s model=%s json_mode=%s", url, self._model, json_mode)
        try:
            resp = requests.post(url, json=payload, timeout=self._timeout)
        except requests.exceptions.RequestException as exc:
            raise OllamaError(
                f"Ollama request failed ({exc}). Is `ollama serve` running at {self._base_url}?"
            ) from exc

        if resp.status_code != 200:
            raise OllamaError(f"Ollama returned status {resp.status_code}: {resp.text[:300]}")

        data = resp.json()
        text = data.get("response", "")
        if not text:
            raise OllamaError("Ollama response had no 'response' text")
        return text
