"""Provider factory: build the LLM client backend.

Currently there is a single local backend (Ollama). The factory keeps a seam so
the rest of the pipeline depends on the ``LLMClient`` interface, not a concrete
class.
"""

from __future__ import annotations

from ..config import Settings
from .base import LLMClient


def build_llm_client(settings: Settings) -> LLMClient:
    """Return the configured LLM client."""
    from .ollama_client import OllamaClient

    return OllamaClient(settings)
