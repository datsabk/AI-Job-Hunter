"""Export stage: write one TXT dossier per relevant job, plus an index.

Fulfils the original goal: a plain-text file per job with the complete details,
contact email, and apply link — plus the AI fit score and any prepared
application draft. An ``index.txt`` lists everything ranked by fit score.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from ..config import Settings
from ..models import ApplyDraft, Job, JobScore
from ..store import Store

logger = logging.getLogger(__name__)


def run_export(settings: Settings, store: Store) -> int:
    """Write a TXT dossier for every relevant job. Returns the number written."""
    out_dir = Path(settings.output_dir) / "jobs"
    out_dir.mkdir(parents=True, exist_ok=True)

    rows = list(store.iter_for_export(settings.score_threshold))
    rows.sort(key=lambda r: r[1].fit_score, reverse=True)

    index_lines = [f"AIJobHunter digest — {_now_str()}", f"{len(rows)} relevant role(s)", ""]

    for job, score, draft in rows:
        path = out_dir / f"{_slug(job)}.txt"
        path.write_text(_render(job, score, draft), encoding="utf-8")
        store.mark_exported(job.source, job.external_id)
        index_lines.append(
            f"[{score.fit_score:3d}] {job.title or '?'} @ {job.company or '?'}"
            f"  ({job.location or 'n/a'})  ->  {path.name}"
        )

    index_path = Path(settings.output_dir) / "index.txt"
    index_path.write_text("\n".join(index_lines) + "\n", encoding="utf-8")
    logger.info("Export: wrote %d dossier(s) and %s", len(rows), index_path)
    return len(rows)


def _render(job: Job, score: JobScore, draft: Optional[ApplyDraft]) -> str:
    lines = [
        "=" * 72,
        f"{job.title or 'Untitled role'}",
        f"{job.company or 'Unknown company'}  |  {job.location or 'Location n/a'}",
        "=" * 72,
        "",
        f"Source        : {job.source}",
        f"Fit score     : {score.fit_score}/100",
        f"Why           : {score.reason}",
        "",
        f"Job link      : {job.url}",
        f"Apply link    : {job.apply_link or job.url}",
        f"Apply channel : {job.apply_channel.value}",
        f"Contact email : {job.contact_email or '(none shown)'}",
        f"Poster        : {job.poster_name or '(n/a)'}  {job.poster_profile}".rstrip(),
        f"Salary        : {job.salary or '(n/a)'}",
        f"Remote        : {job.remote or '(n/a)'}",
        "",
        "-" * 72,
        "JOB DESCRIPTION",
        "-" * 72,
        job.description or "(no description captured)",
        "",
    ]

    if draft is not None:
        lines += [
            "-" * 72,
            f"PREPARED APPLICATION ({draft.channel.value})",
            "-" * 72,
            f"Target        : {draft.target}",
            f"Draft artifact: {draft.artifact_path or '(none)'}",
            f"Notes         : {draft.notes}",
        ]
        if draft.subject:
            lines.append(f"Subject       : {draft.subject}")
        if draft.body:
            lines += ["", "Draft body:", draft.body]
        lines.append("")

    return "\n".join(lines)


def _slug(job: Job) -> str:
    raw = f"{job.company}_{job.title}_{job.external_id}"
    slug = "".join(c if c.isalnum() or c in "-_" else "_" for c in raw)
    return (slug or f"{job.source}_{job.external_id}")[:120]


def _now_str() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
