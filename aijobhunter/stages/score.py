"""On-demand fit assessment: score a single job against the résumé.

This is *not* a bulk stage — it's invoked per job from the TUI. It asks the LLM
how well one job matches the candidate and returns a ``JobScore``. Bulk matching
stays keyword-only; the LLM only ever sees a job the user explicitly picks.
"""

from __future__ import annotations

import logging
from typing import Any

from ..ai.base import LLMClient
from ..models import Job, JobScore

logger = logging.getLogger(__name__)


def score_job(ai: LLMClient, job: Job, profile: dict[str, Any], threshold: int = 70) -> JobScore:
    """Return an LLM fit assessment (0-100 + reason) for a single job."""
    try:
        result = ai.generate_json(_prompt(job, profile))
        fit = max(0, min(100, int(result.get("fit_score", 0))))
        return JobScore(
            fit_score=fit,
            reason=str(result.get("reason", "")),
            recommended=fit >= threshold,
        )
    except Exception as exc:  # noqa: BLE001 - surface a usable result, not a crash
        logger.error("Fit assessment failed for %s/%s: %s", job.source, job.external_id, exc)
        return JobScore(fit_score=0, reason=f"assessment error: {exc}", recommended=False)


def _prompt(job: Job, profile: dict[str, Any]) -> str:
    return "\n".join(
        [
            "You are a career-fit evaluator. Score how well this job matches the candidate.",
            "Return ONLY a JSON object with keys:",
            '  "fit_score" (integer 0-100), "reason" (one or two sentences).',
            "Base the score on skills, seniority, domain, location/remote fit, and the objective.",
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
            f"Description:\n{job.description[:8000]}",
        ]
    )
