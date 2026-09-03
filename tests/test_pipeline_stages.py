"""Integration test for the keyword pipeline: parse → filter → export (CSV)."""

import json
from pathlib import Path

from aijobhunter.config import save_keywords
from aijobhunter.models import RawJob
from aijobhunter.pipeline import run_pipeline
from aijobhunter.store import Store


def _seed_raw(store: Store, ext, title, body):
    payload = {
        "title": title,
        "absolute_url": f"http://gh/{ext}",
        "location": {"name": "Remote"},
        "content": f"<p>{body}</p>",
    }
    store.add_raw(
        RawJob(source="greenhouse", external_id=ext, url=f"http://gh/{ext}",
               raw_text=json.dumps(payload), portal_label="greenhouse:acme")
    )


def test_parse_filter_export_pipeline(settings):
    save_keywords(settings, include=["engineer", "python"], exclude=["intern"])
    with Store(settings.db_path) as store:
        _seed_raw(store, "1", "Backend Engineer", "We use Python and Go.")
        _seed_raw(store, "2", "Sales Manager", "Quotas and CRM.")
        _seed_raw(store, "3", "Engineer Intern", "Learn Python.")

    summary = run_pipeline(settings, ["parse", "filter", "export"])
    assert summary["filter"] == {"kept": 1, "rejected": 2}
    assert summary["export"] == 1

    rows = (Path(settings.output_dir) / "jobs.csv").read_text().splitlines()
    assert rows[0].startswith("keyword_score,matched_keywords,title")
    assert any("Backend Engineer" in r for r in rows[1:])
    assert not any("Sales Manager" in r for r in rows)
    assert not any("Intern" in r for r in rows)
