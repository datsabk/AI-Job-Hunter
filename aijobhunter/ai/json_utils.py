"""Shared helper: pull a JSON object out of a model's text response.

The Ollama client asks the model for JSON but may get it wrapped in prose or a
```json fence. This isolates that tolerant parsing.
"""

from __future__ import annotations

import json
import re
from typing import Any

_FENCE_RE = re.compile(r"```(?:json)?\s*(\{.*?\})\s*```", re.DOTALL)


def extract_json_object(text: str) -> dict[str, Any]:
    """Return the first JSON object found in ``text``. Raises ValueError if none."""
    fence = _FENCE_RE.search(text)
    candidate = fence.group(1) if fence else text
    try:
        return json.loads(candidate)
    except json.JSONDecodeError:
        pass
    start = candidate.find("{")
    end = candidate.rfind("}")
    if start != -1 and end != -1 and end > start:
        return json.loads(candidate[start : end + 1])
    raise ValueError("No JSON object found in response")
