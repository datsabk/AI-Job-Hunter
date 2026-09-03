"""Tests for the on-demand TUI actions (assess fit / draft)."""

from pathlib import Path

from aijobhunter.models import ApplyChannel, Job, RawJob
from aijobhunter.store import Store
from aijobhunter.tui import actions


def _filtered_job(store: Store, **kw) -> Job:
    job = Job(source="greenhouse", external_id="1", url="http://gh/1", **kw)
    store.add_raw(RawJob(source="greenhouse", external_id="1", url="http://gh/1"))
    store.save_parsed(job)
    store.set_filter_result(job, kept=True)
    return job


def test_assess_fit_persists_score(settings, fake_ai, profile):
    with Store(settings.db_path) as store:
        job = _filtered_job(store, title="Backend Engineer", description="Python.")
        score = actions.assess_fit(store, fake_ai, job, profile, settings.score_threshold)
        assert score.fit_score == 85
        assert score.recommended is True
        assert store.get_score("greenhouse", "1").fit_score == 85


def test_draft_application_persists_and_writes_artifact(settings, fake_ai, profile):
    with Store(settings.db_path) as store:
        job = _filtered_job(
            store,
            title="Backend Engineer",
            description="Python.",
            apply_channel=ApplyChannel.GREENHOUSE_FORM,
            apply_link="http://boards.greenhouse.io/acme/jobs/1",
        )
        draft = actions.draft_application(store, fake_ai, job, profile, settings.output_dir)
        assert draft.channel is ApplyChannel.GREENHOUSE_FORM
        assert store.get_draft("greenhouse", "1") is not None
        assert list((Path(settings.output_dir) / "drafts").glob("greenhouse_*.json"))
