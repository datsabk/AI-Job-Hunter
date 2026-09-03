"""Email apply adapter.

Handles jobs that expose a contact email. Uses the LLM to draft a tailored
subject + body from the candidate profile and job description, then writes a
standard ``.eml`` file (optionally with the resume attached) to the drafts
directory. The user reviews and sends it — nothing is transmitted here.
"""

from __future__ import annotations

import logging
from email.message import EmailMessage
from pathlib import Path
from typing import Any

from ..ai.base import LLMClient
from ..models import ApplyChannel, ApplyDraft, Job

logger = logging.getLogger(__name__)


class EmailApply:
    channel = ApplyChannel.EMAIL

    def __init__(self, output_dir: str) -> None:
        self._drafts_dir = Path(output_dir) / "drafts"
        self._drafts_dir.mkdir(parents=True, exist_ok=True)

    def can_handle(self, job: Job) -> bool:
        return bool(job.contact_email)

    def prepare(self, job: Job, profile: dict[str, Any], ai: LLMClient) -> ApplyDraft:
        result = ai.generate_json(_prompt(job, profile))
        subject = str(result.get("subject", f"Application: {job.title}")).strip()
        body = str(result.get("body", "")).strip()

        msg = EmailMessage()
        msg["To"] = job.contact_email
        msg["From"] = profile.get("email", "")
        msg["Subject"] = subject
        msg.set_content(body)

        attachments: list[str] = []
        resume_path = profile.get("resume_attachment")
        if resume_path and Path(resume_path).exists():
            data = Path(resume_path).read_bytes()
            msg.add_attachment(
                data,
                maintype="application",
                subtype="octet-stream",
                filename=Path(resume_path).name,
            )
            attachments.append(resume_path)

        slug = _slug(job)
        artifact = self._drafts_dir / f"{slug}.eml"
        artifact.write_text(msg.as_string(), encoding="utf-8")
        logger.info("EmailApply: wrote draft %s", artifact)

        return ApplyDraft(
            channel=self.channel,
            target=job.contact_email,
            subject=subject,
            body=body,
            attachments=attachments,
            artifact_path=str(artifact),
            notes="Review the .eml draft, then send it from your mail client.",
        )


def _prompt(job: Job, profile: dict[str, Any]) -> str:
    return "\n".join(
        [
            "You are drafting a concise, professional job-application email on behalf of the candidate.",
            "Return ONLY a JSON object: {\"subject\": string, \"body\": string}.",
            "The body must be tailored to the role, reference the candidate's real experience,",
            "stay under 200 words, and never invent facts not present in the resume.",
            "",
            f"Candidate name: {profile.get('name', '')}",
            f"Candidate objective: {profile.get('objective', '')}",
            "Candidate resume:",
            profile.get("resume_text", ""),
            "",
            "Job details:",
            f"Title: {job.title}",
            f"Company: {job.company}",
            f"Location: {job.location}",
            f"Description:\n{job.description[:6000]}",
        ]
    )


def _slug(job: Job) -> str:
    raw = f"email_{job.company}_{job.title}_{job.external_id}"
    return "".join(c if c.isalnum() or c in "-_" else "_" for c in raw)[:120]
