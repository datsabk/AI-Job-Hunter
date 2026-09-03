"""Greenhouse source adapter.

Uses Greenhouse's public boards JSON API (no auth, no browser, near-zero risk):

    https://boards-api.greenhouse.io/v1/boards/<company>/jobs?content=true

Each posting is stored as a ``RawJob`` whose ``raw_text`` is the job's JSON, so
the parser can pull structured fields without re-fetching.
"""

from __future__ import annotations

import json
import logging
from typing import Any

import requests

from ..models import RawJob
from .base import SourceAdapter

logger = logging.getLogger(__name__)

_API = "https://boards-api.greenhouse.io/v1/boards/{company}/jobs?content=true"


class GreenhouseSource(SourceAdapter):
    name = "greenhouse"

    def collect(self, config: dict[str, Any]) -> list[RawJob]:
        company = config.get("company")
        if not company:
            raise ValueError("greenhouse portal entry requires a 'company' board token")

        title_includes = [t.lower() for t in config.get("title_includes", []) if t]
        label = config.get("label", f"greenhouse:{company}")

        url = _API.format(company=company)
        logger.info("Greenhouse: fetching board for '%s'", company)
        resp = requests.get(url, timeout=30, headers={"User-Agent": "AIJobHunter/0.1"})
        if resp.status_code != 200:
            logger.error("Greenhouse board fetch failed status=%s company=%s", resp.status_code, company)
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
                    url=job.get("absolute_url", ""),
                    raw_text=json.dumps(job),
                    portal_label=label,
                )
            )
        logger.info("Greenhouse: collected %d job(s) from '%s'", len(raws), company)
        return raws
