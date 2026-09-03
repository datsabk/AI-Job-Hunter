"""Tests for CSV export of kept (keyword-filtered) jobs."""

import csv
from pathlib import Path

from aijobhunter.models import ApplyChannel, Job, JobScore, RawJob
from aijobhunter.stages.export_csv import run_export_csv
from aijobhunter.store import Store


def _keep(store: Store, ext, title, score=None):
    store.add_raw(RawJob(source="lever", external_id=ext, url=f"http://l/{ext}"))
    job = Job(source="lever", external_id=ext, url=f"http://l/{ext}", title=title,
              company="Acme", apply_channel=ApplyChannel.EXTERNAL_LINK)
    store.save_parsed(job)
    job.keyword_score = len(title.split())
    job.matched_keywords = title.lower().split()
    store.set_filter_result(job, kept=True)
    if score is not None:
        store.save_score(job, JobScore(fit_score=score, reason="ok"))
    return job


def test_export_csv_writes_kept_jobs_ranked(settings):
    with Store(settings.db_path) as store:
        _keep(store, "a", "Engineer, Backend", score=82)   # comma tests escaping; 2 kw hits
        _keep(store, "b", "SRE")                             # 1 kw hit, no score
        n = run_export_csv(settings, store)
        assert n == 2

    csv_path = Path(settings.output_dir) / "jobs.csv"
    with csv_path.open(newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))

    assert len(rows) == 2
    # Ranked by keyword_score desc: the 2-hit job first.
    assert rows[0]["title"] == "Engineer, Backend"
    assert rows[0]["keyword_score"] == "2"
    assert rows[0]["fit_score"] == "82"
    assert rows[1]["title"] == "SRE"
    assert rows[1]["fit_score"] == ""          # unscored → blank
    assert rows[1]["drafted"] == ""


def test_export_csv_excludes_rejected(settings):
    with Store(settings.db_path) as store:
        store.add_raw(RawJob(source="lever", external_id="z", url="http://l/z"))
        job = Job(source="lever", external_id="z", url="http://l/z", title="Chef")
        store.save_parsed(job)
        store.set_filter_result(job, kept=False)
        assert run_export_csv(settings, store) == 0
