"""Base contract for apply adapters.

An ApplyAdapter turns a (job, profile) pair into a reviewable ``ApplyDraft``.
Adapters never send or submit anything on their own — human-in-the-loop is a
hard design rule. ``can_handle`` lets the draft stage pick the right channel per
job (email when an address is shown, Greenhouse when the link is an ATS form).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from ..ai.base import LLMClient
from ..models import ApplyDraft, Job


class ApplyAdapter(ABC):
    """Prepare an application draft for jobs this adapter can handle."""

    def __init__(self, output_dir: str) -> None:
        self._drafts_dir = Path(output_dir) / "drafts"
        self._drafts_dir.mkdir(parents=True, exist_ok=True)

    @abstractmethod
    def can_handle(self, job: Job) -> bool:
        """Return True if this adapter can prepare an application for the job."""

    @abstractmethod
    def prepare(self, job: Job, profile: dict[str, Any], ai: LLMClient) -> ApplyDraft:
        """Build a reviewable application draft."""

    def _safe_slug(self, job: Job) -> str:
        raw = f"{job.company}_{job.title}_{job.external_id}"
        return "".join(c if c.isalnum() or c in "-_" else "_" for c in raw)[:120]
