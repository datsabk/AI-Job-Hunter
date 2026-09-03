"""Tests for pydantic models and their defaults/validation."""

import pytest
from pydantic import ValidationError

from aijobhunter.models import ApplyChannel, ApplyDraft, Job, JobScore, PipelineStatus, RawJob


def test_rawjob_defaults():
    raw = RawJob(source="greenhouse", external_id="1", url="http://x")
    assert raw.raw_text == ""
    assert raw.collected_at is not None


def test_job_defaults_channel_unknown():
    job = Job(source="linkedin", external_id="2", url="http://x")
    assert job.apply_channel is ApplyChannel.UNKNOWN
    assert job.contact_email == ""


def test_jobscore_bounds():
    JobScore(fit_score=0)
    JobScore(fit_score=100)
    with pytest.raises(ValidationError):
        JobScore(fit_score=101)
    with pytest.raises(ValidationError):
        JobScore(fit_score=-1)


def test_applydraft_roundtrip():
    draft = ApplyDraft(channel=ApplyChannel.EMAIL, target="a@b.com", subject="Hi")
    restored = ApplyDraft.model_validate_json(draft.model_dump_json())
    assert restored.channel is ApplyChannel.EMAIL
    assert restored.target == "a@b.com"


def test_pipeline_status_values():
    assert PipelineStatus.COLLECTED.value == "collected"
    assert {s.value for s in PipelineStatus} == {
        "collected", "parsed", "scored", "drafted", "exported"
    }
