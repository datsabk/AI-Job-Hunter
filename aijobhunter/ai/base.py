"""Common LLM client interface.

Any stage that needs the model depends only on this ``LLMClient`` protocol, so
the backend (currently Ollama) stays swappable.
"""

from __future__ import annotations

from typing import Any, Optional, Protocol, runtime_checkable


@runtime_checkable
class LLMClient(Protocol):
    """Minimal text/JSON generation interface implemented by every backend."""

    def generate(self, prompt: str, max_tokens: Optional[int] = None) -> str:
        """Return the model's text response to ``prompt``."""
        ...

    def generate_json(self, prompt: str, max_tokens: Optional[int] = None) -> dict[str, Any]:
        """Return a JSON object parsed from the model's response to ``prompt``."""
        ...
