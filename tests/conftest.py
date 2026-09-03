"""Shared pytest fixtures: temp-scoped Settings and a fake AI client."""

from __future__ import annotations

from typing import Any

import pytest

from aijobhunter.config import Settings


@pytest.fixture
def settings(tmp_path) -> Settings:
    """Settings pointing at temp paths so tests never touch real data/output."""
    s = Settings()
    s.db_path = str(tmp_path / "aijobhunter.db")
    s.output_dir = str(tmp_path / "output")
    s.score_threshold = 70
    return s


class FakeAI:
    """Stand-in for an LLMClient with scripted responses (no network).

    ``generate_json`` routes on the prompt: scoring prompts (which ask for
    "fit_score") get the fit score; everything else gets an enrichment object.
    """

    def __init__(
        self,
        json_result: dict[str, Any] | None = None,
        text_result: str = "",
        enrichment_result: dict[str, Any] | None = None,
    ) -> None:
        self._json = json_result or {"fit_score": 85, "reason": "great match"}
        self._enrichment = enrichment_result or {
            "skills": ["Python", "Go"],
            "seniority": "senior",
            "must_haves": ["distributed systems"],
            "nice_to_haves": [],
            "compensation": "",
            "remote_mode": "remote",
            "summary": "Senior backend role.",
        }
        self._text = text_result or "Dear hiring team, I am a strong fit. Regards, Jane."
        self.json_calls: list[str] = []
        self.text_calls: list[str] = []

    def generate_json(self, prompt: str, max_tokens: int | None = None) -> dict[str, Any]:
        self.json_calls.append(prompt)
        if "fit_score" in prompt:
            return self._json
        return self._enrichment

    def generate(self, prompt: str, max_tokens: int | None = None) -> str:
        self.text_calls.append(prompt)
        return self._text


@pytest.fixture
def fake_ai() -> FakeAI:
    return FakeAI()


@pytest.fixture
def profile() -> dict[str, Any]:
    return {
        "name": "Jane Candidate",
        "email": "jane@example.com",
        "phone": "+1-555-0100",
        "location": "Remote",
        "linkedin": "https://linkedin.com/in/jane",
        "objective": "Senior backend roles",
        "resume_text": "8 years Python and Go distributed systems.",
        "resume_attachment": None,
    }
