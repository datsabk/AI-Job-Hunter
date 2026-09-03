"""SQLite-backed store for the pipeline.

A single ``jobs`` table keyed by ``(source, external_id)`` holds a row per job
and tracks its pipeline status. Structured artifacts (parsed job, score, draft)
are stored as JSON blobs so the schema stays simple and the store stays a thin
persistence layer — each stage reads the rows at its input status, does its
work, and advances the status.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Iterator, Optional

from .models import ApplyDraft, Job, JobScore, PipelineStatus, RawJob

_SCHEMA = """
CREATE TABLE IF NOT EXISTS jobs (
    source          TEXT NOT NULL,
    external_id     TEXT NOT NULL,
    url             TEXT NOT NULL,
    portal_label    TEXT DEFAULT '',
    status          TEXT NOT NULL,
    raw_text        TEXT DEFAULT '',
    collected_at    TEXT NOT NULL,
    job_json        TEXT,
    score_json      TEXT,
    draft_json      TEXT,
    updated_at      TEXT NOT NULL,
    PRIMARY KEY (source, external_id)
);
"""


class Store:
    """Thin SQLite wrapper for the AIJobHunter pipeline."""

    def __init__(self, db_path: str) -> None:
        self._path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(db_path)
        self._conn.row_factory = sqlite3.Row
        self._conn.executescript(_SCHEMA)
        self._migrate()
        self._conn.commit()

    def _migrate(self) -> None:
        """Add columns introduced after a DB was first created."""
        cols = {row["name"] for row in self._conn.execute("PRAGMA table_info(jobs)")}
        for col in ("score_json", "draft_json"):
            if col not in cols:
                self._conn.execute(f"ALTER TABLE jobs ADD COLUMN {col} TEXT")

    def close(self) -> None:
        self._conn.close()

    def __enter__(self) -> "Store":
        return self

    def __exit__(self, *_exc: object) -> None:
        self.close()

    # ---- collect ----

    def exists(self, source: str, external_id: str) -> bool:
        cur = self._conn.execute(
            "SELECT 1 FROM jobs WHERE source = ? AND external_id = ?",
            (source, external_id),
        )
        return cur.fetchone() is not None

    def add_raw(self, raw: RawJob) -> bool:
        """Insert a freshly collected job. Returns False if it already existed."""
        if self.exists(raw.source, raw.external_id):
            return False
        now = _now()
        self._conn.execute(
            """INSERT INTO jobs
               (source, external_id, url, portal_label, status, raw_text,
                collected_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                raw.source,
                raw.external_id,
                raw.url,
                raw.portal_label,
                PipelineStatus.COLLECTED.value,
                raw.raw_text,
                raw.collected_at.isoformat(),
                now,
            ),
        )
        self._conn.commit()
        return True

    # ---- parse ----

    def iter_raw_for_parse(self) -> Iterator[RawJob]:
        for row in self._rows_at(PipelineStatus.COLLECTED):
            yield RawJob(
                source=row["source"],
                external_id=row["external_id"],
                url=row["url"],
                raw_text=row["raw_text"] or "",
                portal_label=row["portal_label"] or "",
                collected_at=_parse_dt(row["collected_at"]),
            )

    def save_parsed(self, job: Job) -> None:
        self._set_json(job.source, job.external_id, "job_json", job.model_dump(mode="json"))
        self._set_status(job.source, job.external_id, PipelineStatus.PARSED)

    # ---- filter (keyword-only) ----

    def iter_jobs_for_filter(self) -> Iterator[Job]:
        """Yield parsed jobs awaiting keyword filtering."""
        yield from self._iter_jobs_at(PipelineStatus.PARSED)

    def set_filter_result(self, job: Job, kept: bool) -> None:
        """Persist the keyword-match result and mark the job kept or rejected."""
        self._set_json(job.source, job.external_id, "job_json", job.model_dump(mode="json"))
        self._set_status(
            job.source,
            job.external_id,
            PipelineStatus.FILTERED if kept else PipelineStatus.REJECTED,
        )

    def iter_filtered(self) -> Iterator[Job]:
        """Yield jobs that passed keyword filtering (for CSV / TUI)."""
        yield from self._iter_jobs_at(PipelineStatus.FILTERED)

    def get_job(self, source: str, external_id: str) -> Optional[Job]:
        row = self._conn.execute(
            "SELECT job_json FROM jobs WHERE source = ? AND external_id = ?",
            (source, external_id),
        ).fetchone()
        return Job.model_validate_json(row["job_json"]) if row and row["job_json"] else None

    # ---- on-demand artifacts (do NOT change pipeline status) ----

    def save_score(self, job: Job, score: JobScore) -> None:
        self._set_json(job.source, job.external_id, "score_json", score.model_dump(mode="json"))

    def get_score(self, source: str, external_id: str) -> Optional[JobScore]:
        row = self._conn.execute(
            "SELECT score_json FROM jobs WHERE source = ? AND external_id = ?",
            (source, external_id),
        ).fetchone()
        return JobScore.model_validate_json(row["score_json"]) if row and row["score_json"] else None

    def save_draft(self, job: Job, draft: ApplyDraft) -> None:
        self._set_json(job.source, job.external_id, "draft_json", draft.model_dump(mode="json"))

    def get_draft(self, source: str, external_id: str) -> Optional[ApplyDraft]:
        row = self._conn.execute(
            "SELECT draft_json FROM jobs WHERE source = ? AND external_id = ?",
            (source, external_id),
        ).fetchone()
        return ApplyDraft.model_validate_json(row["draft_json"]) if row and row["draft_json"] else None

    # ---- helpers ----

    def counts_by_status(self) -> dict[str, int]:
        cur = self._conn.execute("SELECT status, COUNT(*) AS n FROM jobs GROUP BY status")
        return {row["status"]: row["n"] for row in cur.fetchall()}

    def _rows_at(self, status: PipelineStatus) -> list[sqlite3.Row]:
        cur = self._conn.execute("SELECT * FROM jobs WHERE status = ?", (status.value,))
        return cur.fetchall()

    def _iter_jobs_at(self, status: PipelineStatus) -> Iterator[Job]:
        for row in self._rows_at(status):
            if row["job_json"]:
                yield Job.model_validate_json(row["job_json"])

    def _set_json(self, source: str, external_id: str, column: str, value: object) -> None:
        # Column name is internal/whitelisted, never user input.
        self._conn.execute(
            f"UPDATE jobs SET {column} = ?, updated_at = ? WHERE source = ? AND external_id = ?",
            (json.dumps(value), _now(), source, external_id),
        )
        self._conn.commit()

    def _set_status(self, source: str, external_id: str, status: PipelineStatus) -> None:
        self._conn.execute(
            "UPDATE jobs SET status = ?, updated_at = ? WHERE source = ? AND external_id = ?",
            (status.value, _now(), source, external_id),
        )
        self._conn.commit()


def _now() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).isoformat()


def _parse_dt(value: str):
    from datetime import datetime

    return datetime.fromisoformat(value)
