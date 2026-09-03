"""Remotive JSON API source adapter.

Uses Remotive's public, no-auth API (the same "api" source the reference Go tool
uses):

    https://remotive.com/api/remote-jobs?category=<cat>&search=<q>&limit=<n>

Each posting is stored as a ``RawJob`` whose ``raw_text`` is the job JSON so the
parser can extract structured fields without re-fetching.
"""

from __future__ import annotations

import json
import logging
from typing import Any

import requests

from ..models import RawJob
from .base import SourceAdapter

logger = logging.getLogger(__name__)

_API = "https://remotive.com/api/remote-jobs"


class RemotiveSource(SourceAdapter):
    name = "remotive"

    def collect(self, config: dict[str, Any]) -> list[RawJob]:
        params: dict[str, Any] = {}
        if config.get("category"):
            params["category"] = config["category"]
        if config.get("search"):
            params["search"] = config["search"]
        if config.get("limit"):
            params["limit"] = int(config["limit"])

        label = config.get("label", "remotive")
        logger.info("Remotive: fetching %s params=%s", _API, params)
        resp = requests.get(
            _API, params=params, timeout=30, headers={"User-Agent": "AIJobHunter/0.1"}
        )
        if resp.status_code != 200:
            logger.error("Remotive API failed status=%s", resp.status_code)
            return []

        jobs = resp.json().get("jobs", [])
        raws = [
            RawJob(
                source=self.name,
                external_id=str(job.get("id")),
                url=job.get("url", ""),
                raw_text=json.dumps(job),
                portal_label=label,
            )
            for job in jobs
        ]
        logger.info("Remotive: collected %d job(s)", len(raws))
        return raws
