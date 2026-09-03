"""Filter stage: keep jobs by keyword match. Purely keyword-based, no LLM.

Each parsed job is matched against the include/exclude keywords from the
keywords YAML. A job is **kept** (status FILTERED) when it has at least one
include-keyword hit and zero exclude-keyword hits; otherwise it is **rejected**.
The number of include hits becomes ``keyword_score`` (used to rank the CSV), and
the matched keywords are recorded on the job.
"""

from __future__ import annotations

import logging

from ..config import Settings, load_keywords
from ..models import Job
from ..store import Store

logger = logging.getLogger(__name__)


def run_filter(settings: Settings, store: Store) -> dict[str, int]:
    """Filter all parsed jobs by keyword. Returns {kept, rejected}."""
    kw = load_keywords(settings)
    include = [k.lower() for k in kw["include"]]
    exclude = [k.lower() for k in kw["exclude"]]
    if not include and not exclude:
        raise ValueError(
            "No keywords configured. Run `aijobhunter keywords` first to set them."
        )

    kept = rejected = 0
    for job in list(store.iter_jobs_for_filter()):
        keep, score, matched = match_job(job, include, exclude)
        job.keyword_score = score
        job.matched_keywords = matched
        store.set_filter_result(job, keep)
        if keep:
            kept += 1
        else:
            rejected += 1

    logger.info("Filter: kept %d, rejected %d", kept, rejected)
    return {"kept": kept, "rejected": rejected}


def match_job(job: Job, include: list[str], exclude: list[str]) -> tuple[bool, int, list[str]]:
    """Return (keep, keyword_score, matched_keywords) for a job.

    ``include``/``exclude`` are already lowercased. Matching is case-insensitive
    substring matching over the job's title, location, and description.
    """
    haystack = f"{job.title}\n{job.company}\n{job.location}\n{job.description}".lower()

    if any(term in haystack for term in exclude):
        return False, 0, []

    matched = [term for term in include if term in haystack]
    keep = len(matched) > 0
    return keep, len(matched), matched
