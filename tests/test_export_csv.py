"""Tests for CSV export of listed jobs."""

import csv
from pathlib import Path

from aijobhunter.models import ApplyChannel, Job, JobScore, RawJob
from aijobhunter.stages.export_csv import run_export_csv
from aijobhunter.store import Store


def _seed(store: Store):
    # Job with a score, and a comma in the title to test CSV escaping.
    store.add_raw(RawJob(source="lever", external_id="a", url="http://l/a"))
    scored = Job(source="lever", external_id="a", url="http://l/a",
                 title="Engineer, Backend", company="Acme", location="Remote",
                 apply_channel=ApplyChannel.EXTERNAL_LINK, apply_link="http://l/a/apply")
    store.save_parsed(scored)
    store.save_score(scored, JobScore(fit_score=82, reason="strong", recommended=True))

    # Job that was parsed but never scored.
    store.add_raw(RawJob(source="rss", external_id="b", url="http://f/b"))
    store.save_parsed(Job(source="rss", external_id="b", url="http://f/b", title="SRE"))


def test_export_csv_writes_all_parsed_jobs(settings):
    with Store(settings.db_path) as store:
        _seed(store)
        n = run_export_csv(settings, store)
        assert n == 2

    csv_path = Path(settings.output_dir) / "jobs.csv"
    with csv_path.open(newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))

    assert len(rows) == 2
    # Sorted by fit_score desc: the scored job comes first.
    assert rows[0]["title"] == "Engineer, Backend"  # comma preserved via csv quoting
    assert rows[0]["fit_score"] == "82"
    assert rows[0]["recommended"] == "True"
    # Unscored job has blank score fields, not an error.
    assert rows[1]["title"] == "SRE"
    assert rows[1]["fit_score"] == ""


def test_export_csv_custom_path(settings, tmp_path):
    target = tmp_path / "nested" / "out.csv"
    with Store(settings.db_path) as store:
        _seed(store)
        n = run_export_csv(settings, store, str(target))
    assert n == 2
    assert target.exists()
    assert "source,title,company" in target.read_text(encoding="utf-8").splitlines()[0]
