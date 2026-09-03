"""Tests for the SQLite store: dedupe and stage transitions."""

from aijobhunter.models import ApplyChannel, ApplyDraft, Job, JobScore, RawJob
from aijobhunter.store import Store


def _raw(ext="1"):
    return RawJob(source="greenhouse", external_id=ext, url=f"http://x/{ext}", raw_text="{}")


def test_add_raw_dedupes(settings):
    with Store(settings.db_path) as store:
        assert store.add_raw(_raw("1")) is True
        assert store.add_raw(_raw("1")) is False  # duplicate
        assert store.exists("greenhouse", "1")
        assert not store.exists("greenhouse", "999")


def test_full_transition_flow(settings):
    with Store(settings.db_path) as store:
        store.add_raw(_raw("1"))

        # parse
        raws = list(store.iter_raw_for_parse())
        assert len(raws) == 1
        job = Job(source="greenhouse", external_id="1", url="http://x/1", title="Eng")
        store.save_parsed(job)
        assert list(store.iter_raw_for_parse()) == []

        # score
        jobs = list(store.iter_jobs_for_score())
        assert len(jobs) == 1 and jobs[0].title == "Eng"
        store.save_score(job, JobScore(fit_score=90, reason="ok", recommended=True))

        # draft (respects threshold)
        low = list(store.iter_jobs_for_draft(min_score=95))
        assert low == []
        pairs = list(store.iter_jobs_for_draft(min_score=70))
        assert len(pairs) == 1
        store.save_draft(job, ApplyDraft(channel=ApplyChannel.EXTERNAL_LINK, target="http://x/1"))

        # export
        rows = list(store.iter_for_export(min_score=70))
        assert len(rows) == 1
        exported_job, score, draft = rows[0]
        assert exported_job.external_id == "1"
        assert score.fit_score == 90
        assert draft is not None
        store.mark_exported("greenhouse", "1")

        counts = store.counts_by_status()
        assert counts.get("exported") == 1


def test_export_filters_below_threshold(settings):
    with Store(settings.db_path) as store:
        store.add_raw(_raw("2"))
        job = Job(source="greenhouse", external_id="2", url="http://x/2")
        store.save_parsed(job)
        store.save_score(job, JobScore(fit_score=40, reason="weak"))
        assert list(store.iter_for_export(min_score=70)) == []
