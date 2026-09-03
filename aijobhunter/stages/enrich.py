"""Enrich stage: use the LLM to extract structured fields from each job.

Runs llama3 (or whichever provider is configured) over each parsed job's
free-text description and pulls out skills, seniority, must-haves, compensation,
remote mode, and a one-line summary. This structured view sharpens the
downstream ``score`` stage and enriches the CSV export. It is an optional
augmentation: it does not change a job's pipeline status, so ``score`` still
processes the same rows whether or not enrichment ran.
"""

from __future__ import annotations

import logging

from ..ai.base import LLMClient
from ..config import Settings
from ..models import Job, JobEnrichment
from ..store import Store

logger = logging.getLogger(__name__)


def run_enrich(settings: Settings, store: Store, ai: LLMClient) -> int:
    """Extract structured enrichment for every not-yet-enriched parsed job."""
    count = 0
    for job in list(store.iter_jobs_for_enrich()):
        enrichment = _enrich_job(ai, job)
        store.save_enrichment(job, enrichment)
        count += 1
        logger.info("Enrich: %s @ %s -> %d skill(s)", job.title or "?", job.company or "?", len(enrichment.skills))
    logger.info("Enrich: processed %d job(s)", count)
    return count


def _enrich_job(ai: LLMClient, job: Job) -> JobEnrichment:
    try:
        result = ai.generate_json(_prompt(job))
        return JobEnrichment(
            skills=_as_list(result.get("skills")),
            seniority=str(result.get("seniority", "")),
            must_haves=_as_list(result.get("must_haves")),
            nice_to_haves=_as_list(result.get("nice_to_haves")),
            compensation=str(result.get("compensation", "")),
            remote_mode=str(result.get("remote_mode", "")),
            summary=str(result.get("summary", "")),
        )
    except Exception as exc:  # noqa: BLE001 - never let one job stall the stage
        logger.error("Enrich failed for %s/%s: %s", job.source, job.external_id, exc)
        return JobEnrichment()


def _as_list(value: object) -> list[str]:
    if isinstance(value, list):
        return [str(v).strip() for v in value if str(v).strip()]
    if isinstance(value, str) and value.strip():
        return [part.strip() for part in value.split(",") if part.strip()]
    return []


def _prompt(job: Job) -> str:
    return "\n".join(
        [
            "Extract structured facts from the job posting below.",
            "Return ONLY a JSON object with these keys:",
            '  "skills" (array of strings), "seniority" (string: junior/mid/senior/staff/lead),',
            '  "must_haves" (array), "nice_to_haves" (array), "compensation" (string),',
            '  "remote_mode" (string: remote/hybrid/onsite/unknown), "summary" (one sentence).',
            "Use only information present in the posting. Use \"\" or [] when unknown.",
            "",
            f"Title: {job.title}",
            f"Company: {job.company}",
            f"Location: {job.location}",
            f"Description:\n{job.description[:8000]}",
        ]
    )
