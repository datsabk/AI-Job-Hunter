"""Tests for the SQLite store: dedupe, filter transitions, on-demand artifacts."""

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


def test_filter_flow_kept_and_rejected(settings):
    with Store(settings.db_path) as store:
        store.add_raw(_raw("1"))
        store.add_raw(_raw("2"))

        # parse both
        raws = list(store.iter_raw_for_parse())
        assert len(raws) == 2
        keep_job = Job(source="greenhouse", external_id="1", url="http://x/1", title="Eng")
        drop_job = Job(source="greenhouse", external_id="2", url="http://x/2", title="Sales")
        store.save_parsed(keep_job)
        store.save_parsed(drop_job)
        assert len(list(store.iter_jobs_for_filter())) == 2

        # filter: keep #1, reject #2
        keep_job.keyword_score = 2
        keep_job.matched_keywords = ["eng", "python"]
        store.set_filter_result(keep_job, kept=True)
        store.set_filter_result(drop_job, kept=False)

        filtered = list(store.iter_filtered())
        assert len(filtered) == 1
        assert filtered[0].external_id == "1"
        assert filtered[0].keyword_score == 2
        assert filtered[0].matched_keywords == ["eng", "python"]
        assert list(store.iter_jobs_for_filter()) == []  # none left at PARSED

        counts = store.counts_by_status()
        assert counts.get("filtered") == 1
        assert counts.get("rejected") == 1


def test_on_demand_score_and_draft_do_not_change_status(settings):
    with Store(settings.db_path) as store:
        store.add_raw(_raw("1"))
        job = Job(source="greenhouse", external_id="1", url="http://x/1", title="Eng")
        store.save_parsed(job)
        store.set_filter_result(job, kept=True)

        store.save_score(job, JobScore(fit_score=88, reason="great"))
        store.save_draft(job, ApplyDraft(channel=ApplyChannel.EXTERNAL_LINK, target="http://x/1"))

        assert store.get_score("greenhouse", "1").fit_score == 88
        assert store.get_draft("greenhouse", "1").target == "http://x/1"
        # still FILTERED — on-demand artifacts don't advance the pipeline
        assert store.counts_by_status().get("filtered") == 1
        assert list(store.iter_filtered())[0].external_id == "1"


def test_get_job(settings):
    with Store(settings.db_path) as store:
        store.add_raw(_raw("1"))
        store.save_parsed(Job(source="greenhouse", external_id="1", url="http://x/1", title="Eng"))
        assert store.get_job("greenhouse", "1").title == "Eng"
        assert store.get_job("greenhouse", "nope") is None
