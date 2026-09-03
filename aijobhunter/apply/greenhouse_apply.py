"""Greenhouse form apply adapter.

Greenhouse application forms are public (no login). This adapter prepares the
data you'd paste into that form: standard identity fields mapped from your
profile plus an AI-drafted cover letter. It writes the mapped fields to a JSON
artifact for review. Actual form submission is intentionally left to you
(human-in-the-loop); auto-submitting a form in your name is out of scope for v1.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from ..ai.base import LLMClient
from ..models import ApplyChannel, ApplyDraft, Job

logger = logging.getLogger(__name__)


class GreenhouseApply:
    channel = ApplyChannel.GREENHOUSE_FORM

    def __init__(self, output_dir: str) -> None:
        self._drafts_dir = Path(output_dir) / "drafts"
        self._drafts_dir.mkdir(parents=True, exist_ok=True)

    def can_handle(self, job: Job) -> bool:
        return job.apply_channel == ApplyChannel.GREENHOUSE_FORM or "greenhouse" in (
            job.apply_link or ""
        )

    def prepare(self, job: Job, profile: dict[str, Any], ai: LLMClient) -> ApplyDraft:
        cover_letter = ai.generate(_cover_letter_prompt(job, profile)).strip()

        full_name = profile.get("name", "").strip()
        first, _, last = full_name.partition(" ")
        form_fields = {
            "first_name": first,
            "last_name": last,
            "email": profile.get("email", ""),
            "phone": profile.get("phone", ""),
            "location": profile.get("location", ""),
            "linkedin_profile": profile.get("linkedin", ""),
            "resume": profile.get("resume_attachment", ""),
            "cover_letter": cover_letter,
        }

        slug = _slug(job)
        artifact = self._drafts_dir / f"{slug}.json"
        artifact.write_text(
            json.dumps({"apply_url": job.apply_link, "fields": form_fields}, indent=2),
            encoding="utf-8",
        )
        logger.info("GreenhouseApply: wrote draft %s", artifact)

        return ApplyDraft(
            channel=self.channel,
            target=job.apply_link,
            body=cover_letter,
            form_fields=form_fields,
            artifact_path=str(artifact),
            notes="Open the apply URL and paste these fields. Review before submitting.",
        )


def _cover_letter_prompt(job: Job, profile: dict[str, Any]) -> str:
    return "\n".join(
        [
            "Write a concise, professional cover letter (under 250 words) for this role.",
            "Use only facts present in the candidate's resume; do not invent anything.",
            "Return plain text only (no preamble, no markdown headers).",
            "",
            f"Candidate: {profile.get('name', '')}",
            f"Objective: {profile.get('objective', '')}",
            "Resume:",
            profile.get("resume_text", ""),
            "",
            f"Role: {job.title} at {job.company} ({job.location})",
            f"Description:\n{job.description[:6000]}",
        ]
    )


def _slug(job: Job) -> str:
    raw = f"greenhouse_{job.company}_{job.title}_{job.external_id}"
    return "".join(c if c.isalnum() or c in "-_" else "_" for c in raw)[:120]
