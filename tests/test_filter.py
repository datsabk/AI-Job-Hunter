"""Tests for the keyword filter stage."""

import pytest

from aijobhunter.config import save_keywords
from aijobhunter.models import Job, RawJob
from aijobhunter.stages.filter import match_job, run_filter
from aijobhunter.store import Store


def _job(title="", company="", location="", description=""):
    return Job(source="s", external_id="1", url="u", title=title, company=company,
               location=location, description=description)


def test_match_keep_on_include_hit():
    keep, score, matched = match_job(
        _job(title="Senior Python Engineer", description="distributed systems"),
        include=["python", "go", "distributed systems"],
        exclude=[],
    )
    assert keep is True
    assert score == 2
    assert set(matched) == {"python", "distributed systems"}


def test_match_reject_on_exclude_hit():
    keep, score, matched = match_job(
        _job(title="Python Intern"),
        include=["python"],
        exclude=["intern"],
    )
    assert keep is False
    assert score == 0
    assert matched == []


def test_match_reject_when_no_include_hit():
    keep, score, matched = match_job(
        _job(title="Marketing Manager"),
        include=["python", "go"],
        exclude=[],
    )
    assert keep is False


def test_run_filter_uses_config_and_transitions(settings):
    save_keywords(settings, include=["python"], exclude=["intern"])
    with Store(settings.db_path) as store:
        for ext, title in [("1", "Python Engineer"), ("2", "Python Intern"), ("3", "Chef")]:
            store.add_raw(RawJob(source="s", external_id=ext, url=f"u/{ext}"))
            store.save_parsed(Job(source="s", external_id=ext, url=f"u/{ext}", title=title))

        result = run_filter(settings, store)
        assert result == {"kept": 1, "rejected": 2}
        kept = list(store.iter_filtered())
        assert [j.external_id for j in kept] == ["1"]
        assert kept[0].matched_keywords == ["python"]


def test_run_filter_errors_without_keywords(settings):
    save_keywords(settings, include=[], exclude=[])
    with Store(settings.db_path) as store:
        with pytest.raises(ValueError, match="No keywords configured"):
            run_filter(settings, store)
