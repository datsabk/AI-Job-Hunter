"""Shared pytest fixtures: temp-scoped Settings and a fake LLM client."""

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
    s.keywords_config = str(tmp_path / "keywords.yaml")
    s.score_threshold = 70
    s.batch_size = 5
    return s


class FakeAI:
    """Stand-in for an LLMClient with scripted responses (no network).

    ``generate_json`` routes on the prompt: keyword-extraction prompts (which ask
    for "keywords") get a keyword list; fit-assessment prompts (which ask for
    "fit_score") get a score.
    """

    def __init__(
        self,
        score_result: dict[str, Any] | None = None,
        keywords_result: dict[str, Any] | None = None,
        text_result: str = "",
    ) -> None:
        self._score = score_result or {"fit_score": 85, "reason": "great match"}
        self._keywords = keywords_result or {"keywords": ["python", "go", "platform engineer"]}
        self._text = text_result or "Dear hiring team, I am a strong fit. Regards, Jane."
        self.json_calls: list[str] = []
        self.text_calls: list[str] = []

    def generate_json(self, prompt: str, max_tokens: int | None = None) -> dict[str, Any]:
        self.json_calls.append(prompt)
        if "keywords" in prompt.lower():
            return self._keywords
        return self._score

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
