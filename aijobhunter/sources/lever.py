"""Lever public postings API source adapter.

Lever exposes a company's board as public JSON (no auth):

    https://api.lever.co/v0/postings/<company>?mode=json

``company`` is the board token from a URL like ``jobs.lever.co/<company>``.
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

_API = "https://api.lever.co/v0/postings/{company}?mode=json"


class LeverSource(SourceAdapter):
    name = "lever"

    def collect(self, config: dict[str, Any]) -> list[RawJob]:
        company = config.get("company")
        if not company:
            raise ValueError("lever portal entry requires a 'company' board token")

        title_includes = [t.lower() for t in config.get("title_includes", []) if t]
        label = config.get("label", f"lever:{company}")

        url = _API.format(company=company)
        logger.info("Lever: fetching board for '%s'", company)
        resp = requests.get(url, timeout=30, headers={"User-Agent": "AIJobHunter/0.1"})
        if resp.status_code != 200:
            logger.error("Lever board fetch failed status=%s company=%s", resp.status_code, company)
            return []

        postings = resp.json()
        raws: list[RawJob] = []
        for post in postings:
            title = (post.get("text") or "").lower()
            if title_includes and not any(t in title for t in title_includes):
                continue
            raws.append(
                RawJob(
                    source=self.name,
                    external_id=str(post.get("id")),
                    url=post.get("hostedUrl", ""),
                    raw_text=json.dumps(post),
                    portal_label=label,
                )
            )
        logger.info("Lever: collected %d job(s) from '%s'", len(raws), company)
        return raws
