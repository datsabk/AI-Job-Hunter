"""Generic RSS/Atom job-feed source adapter.

Mirrors the reference Go tool's "rss" source kind: point it at one or more job
feeds (Remotive, We Work Remotely, Real Work From Anywhere, etc.) and it yields a
``RawJob`` per entry. Feed titles vary wildly in how they encode company vs.
role, so a small heuristic splits them here and the structured result is stored
as JSON for the parser.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Optional

from ..models import RawJob
from .base import SourceAdapter

logger = logging.getLogger(__name__)


class RSSSource(SourceAdapter):
    name = "rss"

    def collect(self, config: dict[str, Any]) -> list[RawJob]:
        try:
            import feedparser
        except ImportError as exc:  # pragma: no cover - optional dep guard
            raise RuntimeError(
                "feedparser is required for the RSS adapter (pip install -r requirements.txt)"
            ) from exc

        feeds = self._feed_entries(config)
        if not feeds:
            raise ValueError("rss portal entry requires 'url' or a non-empty 'feeds' list")

        raws: list[RawJob] = []
        seen: set[str] = set()
        for feed in feeds:
            url = feed["url"]
            label = feed.get("label", f"rss:{url}")
            logger.info("RSS: fetching %s", url)
            try:
                parsed = feedparser.parse(url)
            except Exception as exc:  # noqa: BLE001 - one bad feed must not kill the run
                logger.error("RSS: failed to parse %s: %s", url, exc)
                continue

            for entry in parsed.entries:
                ext_id = (getattr(entry, "id", "") or getattr(entry, "link", "")).strip()
                if not ext_id or ext_id in seen:
                    continue
                seen.add(ext_id)
                raws.append(self._to_raw(entry, ext_id, label))

        logger.info("RSS: collected %d entrie(s) across %d feed(s)", len(raws), len(feeds))
        return raws

    @staticmethod
    def _feed_entries(config: dict[str, Any]) -> list[dict[str, Any]]:
        feeds = list(config.get("feeds", []))
        if config.get("url"):
            feeds.append({"url": config["url"], "label": config.get("label", "rss")})
        return [f for f in feeds if f.get("url")]

    def _to_raw(self, entry: Any, ext_id: str, label: str) -> RawJob:
        raw_title = (getattr(entry, "title", "") or "").strip()
        author = ""
        if getattr(entry, "author", None):
            author = entry.author.strip()
        title, company = _split_title_company(raw_title, author)

        payload = {
            "title": title,
            "company": company,
            "location": _first_tag_location(entry),
            "description_html": getattr(entry, "summary", "") or "",
            "link": getattr(entry, "link", "") or "",
            "published": getattr(entry, "published", "") or "",
        }
        return RawJob(
            source=self.name,
            external_id=ext_id,
            url=payload["link"],
            raw_text=json.dumps(payload),
            portal_label=label,
        )


def _split_title_company(raw_title: str, author: str) -> tuple[str, str]:
    """Best-effort split of a feed title into (title, company)."""
    if not raw_title:
        return "", author or "Unknown"
    # "Role at Company"
    if " at " in raw_title:
        title, _, company = raw_title.rpartition(" at ")
        return title.strip(), company.strip()
    # "Company: Role" (We Work Remotely style)
    if ": " in raw_title:
        company, _, title = raw_title.partition(": ")
        return title.strip(), company.strip()
    return raw_title, (author or "Unknown")


def _first_tag_location(entry: Any) -> str:
    location = getattr(entry, "location", "") or ""
    if location:
        return str(location).strip()
    return ""
