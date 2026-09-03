"""Ashby public job-board API source adapter.

Ashby exposes a company's board as public JSON (no auth):

    https://api.ashbyhq.com/posting-api/job-board/<board>?includeCompensation=true

``board`` is the job-board name from a URL like ``jobs.ashbyhq.com/<board>``.
Each posting is stored as a ``RawJob`` carrying the posting JSON.
"""

from __future__ import annotations

import json
import logging
from typing import Any

import requests

from ..models import RawJob
from .base import SourceAdapter

logger = logging.getLogger(__name__)

_API = "https://api.ashbyhq.com/posting-api/job-board/{board}"


class AshbySource(SourceAdapter):
    name = "ashby"

    def collect(self, config: dict[str, Any]) -> list[RawJob]:
        board = config.get("company") or config.get("board")
        if not board:
            raise ValueError("ashby portal entry requires a 'company' (job-board) token")

        title_includes = [t.lower() for t in config.get("title_includes", []) if t]
        label = config.get("label", f"ashby:{board}")

        url = _API.format(board=board)
        logger.info("Ashby: fetching board for '%s'", board)
        resp = requests.get(
            url,
            params={"includeCompensation": "true"},
            timeout=30,
            headers={"User-Agent": "AIJobHunter/0.1"},
        )
        if resp.status_code != 200:
            logger.error("Ashby board fetch failed status=%s board=%s", resp.status_code, board)
            return []

        jobs = resp.json().get("jobs", [])
        raws: list[RawJob] = []
        for job in jobs:
            title = (job.get("title") or "").lower()
            if title_includes and not any(t in title for t in title_includes):
                continue
            raws.append(
                RawJob(
                    source=self.name,
                    external_id=str(job.get("id")),
                    url=job.get("jobUrl", "") or job.get("applyUrl", ""),
                    raw_text=json.dumps(job),
                    portal_label=label,
                )
            )
        logger.info("Ashby: collected %d job(s) from '%s'", len(raws), board)
        return raws
