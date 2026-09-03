"""CSV export: write every listed (parsed) job to a CSV file.

Unlike the ``export`` stage (which writes rich TXT dossiers only for high-fit
roles), this exports the full listing — every job collected and parsed so far,
with its fit score when available — into a single spreadsheet-friendly CSV. This
mirrors the CSV export added to the reference TUI: "export the jobs currently
listed."
"""

from __future__ import annotations

import csv
import logging
import sys
from pathlib import Path
from typing import Optional, TextIO

from ..config import Settings
from ..models import Job, JobEnrichment, JobScore
from ..store import Store

logger = logging.getLogger(__name__)

# Column order for the exported CSV.
_COLUMNS = [
    "source",
    "title",
    "company",
    "location",
    "remote",
    "salary",
    "fit_score",
    "recommended",
    "reason",
    "seniority",
    "skills",
    "remote_mode",
    "contact_email",
    "apply_channel",
    "apply_link",
    "url",
    "posted_at",
    "external_id",
]


def run_export_csv(settings: Settings, store: Store, path: Optional[str] = None) -> int:
    """Write all parsed jobs to CSV. ``path='-'`` writes to stdout.

    Returns the number of rows written.
    """
    rows = [
        (job, score, store.get_enrichment(job.source, job.external_id))
        for job, score in store.iter_all_jobs()
    ]
    rows.sort(key=lambda r: (r[1].fit_score if r[1] else -1), reverse=True)

    target = path or str(Path(settings.output_dir) / "jobs.csv")
    if target == "-":
        return _write(sys.stdout, rows)

    out_path = Path(target)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8", newline="") as fh:
        count = _write(fh, rows)
    logger.info("CSV export: wrote %d row(s) to %s", count, out_path)
    return count


def _write(
    fh: TextIO, rows: list[tuple[Job, Optional[JobScore], Optional[JobEnrichment]]]
) -> int:
    writer = csv.DictWriter(fh, fieldnames=_COLUMNS, extrasaction="ignore")
    writer.writeheader()
    for job, score, enrichment in rows:
        writer.writerow(_row(job, score, enrichment))
    return len(rows)


def _row(
    job: Job, score: Optional[JobScore], enrichment: Optional[JobEnrichment]
) -> dict[str, object]:
    return {
        "source": job.source,
        "title": job.title,
        "company": job.company,
        "location": job.location,
        "remote": job.remote,
        "salary": job.salary,
        "fit_score": score.fit_score if score else "",
        "recommended": score.recommended if score else "",
        "reason": score.reason if score else "",
        "seniority": enrichment.seniority if enrichment else "",
        "skills": ", ".join(enrichment.skills) if enrichment else "",
        "remote_mode": enrichment.remote_mode if enrichment else "",
        "contact_email": job.contact_email,
        "apply_channel": job.apply_channel.value,
        "apply_link": job.apply_link or job.url,
        "url": job.url,
        "posted_at": job.posted_at,
        "external_id": job.external_id,
    }
