"""Keyword extraction from the résumé (the one place ``run`` never touches).

The ``keywords`` command uses this once, interactively: the LLM proposes search
keywords from the candidate's résumé; the CLI then lets the user edit them and
add exclusion keywords. The result is saved to the keywords YAML and drives the
purely-keyword-based filter stage.
"""

from __future__ import annotations

import logging
from typing import Any

from ..ai.base import LLMClient

logger = logging.getLogger(__name__)


def extract_keywords(ai: LLMClient, profile: dict[str, Any], limit: int = 25) -> list[str]:
    """Ask the LLM for search keywords derived from the résumé/objective."""
    try:
        result = ai.generate_json(_prompt(profile, limit))
        raw = result.get("keywords", [])
        seen: set[str] = set()
        keywords: list[str] = []
        for item in raw:
            kw = str(item).strip()
            key = kw.lower()
            if kw and key not in seen:
                seen.add(key)
                keywords.append(kw)
        return keywords[:limit]
    except Exception as exc:  # noqa: BLE001 - keyword extraction is best-effort
        logger.error("Keyword extraction failed: %s", exc)
        return []


def _prompt(profile: dict[str, Any], limit: int) -> str:
    return "\n".join(
        [
            "You extract job-search keywords from a candidate's résumé.",
            f"Return ONLY a JSON object: {{\"keywords\": [up to {limit} strings]}}.",
            "Keywords should be concrete role titles, technologies, and domains the",
            "candidate should search for (e.g. 'platform engineer', 'kubernetes',",
            "'python', 'distributed systems'). Lowercase, no duplicates, no fluff.",
            "",
            f"Objective: {profile.get('objective', '')}",
            "Résumé:",
            profile.get("resume_text", ""),
        ]
    )
