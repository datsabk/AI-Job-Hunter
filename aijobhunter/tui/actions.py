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
