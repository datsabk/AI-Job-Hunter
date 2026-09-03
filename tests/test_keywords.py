"""Tests for résumé keyword extraction and keywords config load/save."""

from aijobhunter.config import load_keywords, save_keywords
from aijobhunter.stages.keywords import extract_keywords


def test_extract_keywords_dedupes_and_limits(fake_ai, profile):
    fake_ai._keywords = {"keywords": ["Python", "python", "Go", "Kubernetes", ""]}
    kws = extract_keywords(fake_ai, profile, limit=3)
    assert kws == ["Python", "Go", "Kubernetes"]  # dedup case-insensitive, blanks dropped, capped


def test_extract_keywords_prompt_asks_for_keywords(fake_ai, profile):
    extract_keywords(fake_ai, profile)
    assert any("keywords" in p.lower() for p in fake_ai.json_calls)


def test_extract_keywords_handles_bad_response(profile):
    class Boom:
        def generate_json(self, *a, **k):
            raise RuntimeError("nope")

        def generate(self, *a, **k):
            return ""

    assert extract_keywords(Boom(), profile) == []


def test_keywords_config_roundtrip(settings):
    path = save_keywords(settings, include=["python", "go"], exclude=["intern"])
    assert path == settings.keywords_config
    loaded = load_keywords(settings)
    assert loaded == {"include": ["python", "go"], "exclude": ["intern"]}
