"""CSV export: write every kept (keyword-filtered) job to a CSV file.

Ranked by ``keyword_score`` (include-keyword hits). LLM-derived columns
(``fit_score``/``reason``) and ``drafted`` fill in only for jobs you've assessed
or drafted on demand from the TUI.
"""

from __future__ import annotations

import csv
import logging
import sys
from pathlib import Path
from typing import Optional, TextIO

from ..config import Settings
from ..models import Job
from ..store import Store

logger = logging.getLogger(__name__)

_COLUMNS = [
    "keyword_score",
    "matched_keywords",
    "title",
    "company",
    "location",
    "remote",
    "salary",
    "fit_score",
    "fit_reason",
    "drafted",
    "contact_email",
    "apply_channel",
    "apply_link",
    "url",
    "posted_at",
    "source",
    "external_id",
]


def run_export_csv(settings: Settings, store: Store, path: Optional[str] = None) -> int:
    """Write all kept jobs to CSV. ``path='-'`` writes to stdout. Returns row count."""
    jobs = sorted(store.iter_filtered(), key=lambda j: j.keyword_score, reverse=True)

    target = path or str(Path(settings.output_dir) / "jobs.csv")
    if target == "-":
        return _write(sys.stdout, jobs, store)

    out_path = Path(target)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8", newline="") as fh:
        count = _write(fh, jobs, store)
    logger.info("CSV export: wrote %d row(s) to %s", count, out_path)
    return count


def _write(fh: TextIO, jobs: list[Job], store: Store) -> int:
    writer = csv.DictWriter(fh, fieldnames=_COLUMNS, extrasaction="ignore")
    writer.writeheader()
    for job in jobs:
        score = store.get_score(job.source, job.external_id)
        draft = store.get_draft(job.source, job.external_id)
        writer.writerow(
            {
                "keyword_score": job.keyword_score,
                "matched_keywords": "; ".join(job.matched_keywords),
                "title": job.title,
                "company": job.company,
                "location": job.location,
                "remote": job.remote,
                "salary": job.salary,
                "fit_score": score.fit_score if score else "",
                "fit_reason": score.reason if score else "",
                "drafted": "yes" if draft else "",
                "contact_email": job.contact_email,
                "apply_channel": job.apply_channel.value,
                "apply_link": job.apply_link or job.url,
                "url": job.url,
                "posted_at": job.posted_at,
                "source": job.source,
                "external_id": job.external_id,
            }
        )
    return len(jobs)
