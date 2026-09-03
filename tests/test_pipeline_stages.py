"""Integration tests for score -> draft -> export using a fake AI client."""

from pathlib import Path

from aijobhunter.models import ApplyChannel, Job
from aijobhunter.stages import draft as draft_stage
from aijobhunter.stages import export as export_stage
from aijobhunter.stages import score as score_stage
from aijobhunter.store import Store


def _seed_parsed_job(store: Store) -> Job:
    job = Job(
        source="greenhouse",
        external_id="101",
        url="http://gh/101",
        title="Backend Engineer",
        company="acme",
        location="Remote",
        description="Build APIs in Python.",
        apply_link="http://boards.greenhouse.io/acme/jobs/101",
        apply_channel=ApplyChannel.GREENHOUSE_FORM,
    )
    # Insert as raw then advance to parsed so the row exists.
    from aijobhunter.models import RawJob

    store.add_raw(RawJob(source="greenhouse", external_id="101", url="http://gh/101"))
    store.save_parsed(job)
    return job


def test_score_stage_writes_scores(settings, fake_ai, profile):
    with Store(settings.db_path) as store:
        _seed_parsed_job(store)
        n = score_stage.run_score(settings, store, fake_ai, profile)
        assert n == 1
        pairs = list(store.iter_jobs_for_draft(min_score=70))
        assert len(pairs) == 1
        assert pairs[0][1].fit_score == 85


def test_draft_stage_uses_greenhouse_adapter(settings, fake_ai, profile):
    with Store(settings.db_path) as store:
        _seed_parsed_job(store)
        score_stage.run_score(settings, store, fake_ai, profile)
        n = draft_stage.run_draft(settings, store, fake_ai, profile)
        assert n == 1
        # A greenhouse JSON draft artifact should exist.
        drafts = list((Path(settings.output_dir) / "drafts").glob("greenhouse_*.json"))
        assert len(drafts) == 1


def test_export_writes_dossier_and_index(settings, fake_ai, profile):
    with Store(settings.db_path) as store:
        _seed_parsed_job(store)
        score_stage.run_score(settings, store, fake_ai, profile)
        draft_stage.run_draft(settings, store, fake_ai, profile)
        n = export_stage.run_export(settings, store)
        assert n == 1

    dossiers = list((Path(settings.output_dir) / "jobs").glob("*.txt"))
    assert len(dossiers) == 1
    text = dossiers[0].read_text()
    assert "Backend Engineer" in text
    assert "Fit score     : 85/100" in text
    assert "Apply link" in text

    index = (Path(settings.output_dir) / "index.txt").read_text()
    assert "Backend Engineer" in index
