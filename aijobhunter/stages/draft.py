"""On-demand application drafting for a single job.

Invoked per job from the TUI. Picks the best apply channel — email when the
posting exposes an address, Greenhouse when the apply link is an ATS form,
otherwise a plain external-link fallback — and returns a reviewable draft.
Nothing is ever sent or submitted.
"""

from __future__ import annotations

import logging
from typing import Any

from ..ai.base import LLMClient
from ..apply.email_apply import EmailApply
from ..apply.greenhouse_apply import GreenhouseApply
from ..models import ApplyChannel, ApplyDraft, Job

logger = logging.getLogger(__name__)


def prepare_draft(job: Job, profile: dict[str, Any], ai: LLMClient, output_dir: str) -> ApplyDraft:
    """Prepare a reviewable application draft for one job."""
    adapters = [EmailApply(output_dir), GreenhouseApply(output_dir)]
    for adapter in adapters:
        try:
            if adapter.can_handle(job):
                return adapter.prepare(job, profile, ai)
        except Exception as exc:  # noqa: BLE001 - fall through to the link fallback
            logger.error("Apply adapter %s failed for %s: %s", type(adapter).__name__, job.url, exc)

    return ApplyDraft(
        channel=ApplyChannel.EXTERNAL_LINK,
        target=job.apply_link or job.url,
        notes="No supported apply channel detected — apply manually via the link.",
    )
