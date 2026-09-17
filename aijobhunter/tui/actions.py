"""On-demand actions invoked from the TUI — the testable core (no Textual here).

Each function acts on a single job, calls the LLM once, persists the result, and
returns it. The Textual layer is a thin shell over these.
"""

from __future__ import annotations

from typing import Any

from ..ai.base import LLMClient
from ..models import ApplyDraft, Job, JobScore
from ..stages.draft import prepare_draft
from ..stages.score import score_job
from ..store import Store


def assess_fit(
    store: Store, ai: LLMClient, job: Job, profile: dict[str, Any], threshold: int = 70
) -> JobScore:
    """Run an LLM fit assessment for one job, persist it, and return it."""
    score = score_job(ai, job, profile, threshold)
    store.save_score(job, score)
    return score


def draft_application(
    store: Store, ai: LLMClient, job: Job, profile: dict[str, Any], output_dir: str
) -> ApplyDraft:
    """Prepare an application draft for one job, persist it, and return it."""
    draft = prepare_draft(job, profile, ai, output_dir)
    store.save_draft(job, draft)
    return draft


def run_actions(
    kind: str,
    db_path: str,
    ai: LLMClient,
    jobs: list[Job],
    profile: dict[str, Any],
    *,
    score_threshold: int,
    output_dir: str,
) -> list[tuple[Job, Exception]]:
    """Run ``assess`` or ``draft`` over ``jobs`` using a thread-local Store.

    Opens its OWN SQLite connection (sqlite3 connections are confined to the
    thread that created them), so this is safe to call from a background worker
    thread. Writes are committed as they happen, so a connection on another
    thread will see the results afterwards. Returns ``(job, exception)`` pairs
    for jobs that failed, so the caller can report them without aborting the run.
    """
    errors: list[tuple[Job, Exception]] = []
    with Store(db_path) as store:
        for job in jobs:
            try:
                if kind == "assess":
                    assess_fit(store, ai, job, profile, score_threshold)
                else:
                    draft_application(store, ai, job, profile, output_dir)
            except Exception as exc:  # noqa: BLE001 - collect, don't abort the batch
                errors.append((job, exc))
    return errors
