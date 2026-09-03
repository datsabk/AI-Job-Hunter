"""Draft stage: prepare a reviewable application for each high-fit job.

Picks the best apply channel per job: email when the posting exposes an address,
Greenhouse when the apply link is an ATS form, otherwise a plain external-link
fallback (no auto-anything — the user just gets the link). All drafts are for
review only; nothing is sent or submitted.
"""

from __future__ import annotations

import logging
from typing import Any

from ..ai.base import LLMClient
from ..apply.email_apply import EmailApply
from ..apply.greenhouse_apply import GreenhouseApply
from ..config import Settings
from ..models import ApplyChannel, ApplyDraft, Job
from ..store import Store

logger = logging.getLogger(__name__)


def run_draft(settings: Settings, store: Store, ai: LLMClient, profile: dict[str, Any]) -> int:
    """Draft applications for jobs above the score threshold. Returns count drafted."""
    adapters = [EmailApply(settings.output_dir), GreenhouseApply(settings.output_dir)]
    count = 0

    for job, score in list(store.iter_jobs_for_draft(settings.score_threshold)):
        draft = _prepare(job, profile, ai, adapters)
        store.save_draft(job, draft)
        count += 1
        logger.info("Draft: %s @ %s via %s", job.title or "?", job.company or "?", draft.channel.value)

    logger.info("Draft: prepared %d application(s)", count)
    return count


def _prepare(job: Job, profile: dict[str, Any], ai: LLMClient, adapters: list[Any]) -> ApplyDraft:
    for adapter in adapters:
        try:
            if adapter.can_handle(job):
                return adapter.prepare(job, profile, ai)
        except Exception as exc:  # noqa: BLE001 - fall through to the link fallback
            logger.error("Apply adapter %s failed for %s: %s", type(adapter).__name__, job.url, exc)

    # Fallback: hand the user the link, no application prepared.
    return ApplyDraft(
        channel=ApplyChannel.EXTERNAL_LINK,
        target=job.apply_link or job.url,
        notes="No supported apply channel detected — apply manually via the link.",
    )
