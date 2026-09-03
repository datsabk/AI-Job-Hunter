"""Score stage: ask the LLM how well each job fits the candidate profile.

Uses the configured provider (Ollama by default). When a job has been enriched,
the extracted structured fields are included in the prompt to ground the score.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from ..ai.base import LLMClient
from ..config import Settings
from ..models import Job, JobEnrichment, JobScore
from ..store import Store

logger = logging.getLogger(__name__)


def run_score(settings: Settings, store: Store, ai: LLMClient, profile: dict[str, Any]) -> int:
    """Score all parsed jobs against the profile. Returns the number scored."""
    threshold = settings.score_threshold
    count = 0
    for job in list(store.iter_jobs_for_score()):
        enrichment = store.get_enrichment(job.source, job.external_id)
        score = _score_job(ai, job, profile, threshold, enrichment)
        store.save_score(job, score)
        count += 1
        logger.info("Score: %s @ %s -> %d", job.title or "?", job.company or "?", score.fit_score)
    logger.info("Score: processed %d job(s)", count)
    return count


def _score_job(
    ai: LLMClient,
    job: Job,
    profile: dict[str, Any],
    threshold: int,
    enrichment: Optional[JobEnrichment],
) -> JobScore:
    try:
        result = ai.generate_json(_prompt(job, profile, enrichment))
        fit = int(result.get("fit_score", 0))
        fit = max(0, min(100, fit))
        return JobScore(
            fit_score=fit,
            reason=str(result.get("reason", "")),
            recommended=fit >= threshold,
        )
    except Exception as exc:  # noqa: BLE001 - one bad response must not stall the stage
        logger.error("Score failed for %s/%s: %s", job.source, job.external_id, exc)
        return JobScore(fit_score=0, reason=f"scoring error: {exc}", recommended=False)


def _prompt(job: Job, profile: dict[str, Any], enrichment: Optional[JobEnrichment]) -> str:
    lines = [
        "You are a career-fit evaluator. Score how well this job matches the candidate.",
        "Return ONLY a JSON object with keys:",
        '  "fit_score" (integer 0-100), "reason" (one or two sentences).',
        "Base the score on skills, seniority, domain, location/remote fit, and the stated objective.",
        "Be honest and calibrated; do not inflate scores.",
        "",
        f"Candidate objective: {profile.get('objective', '')}",
        "Candidate resume:",
        profile.get("resume_text", ""),
        "",
        "Job:",
        f"Title: {job.title}",
        f"Company: {job.company}",
        f"Location: {job.location}",
    ]
    if enrichment is not None:
        lines += [
            "",
            "Extracted structured facts about this job:",
            f"  Seniority: {enrichment.seniority}",
            f"  Skills: {', '.join(enrichment.skills)}",
            f"  Must-haves: {', '.join(enrichment.must_haves)}",
            f"  Remote mode: {enrichment.remote_mode}",
            f"  Compensation: {enrichment.compensation}",
        ]
    lines += ["", f"Description:\n{job.description[:8000]}"]
    return "\n".join(lines)
