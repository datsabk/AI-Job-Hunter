"""Parse stage: turn raw payloads into structured ``Job`` records.

Dispatches on the source: Greenhouse payloads are JSON, LinkedIn payloads are
HTML. Parsers are defensive — a missing field yields an empty string rather than
an error, so one malformed posting never stalls the pipeline.
"""

from __future__ import annotations

import html
import json
import logging
import re
from typing import Optional

from bs4 import BeautifulSoup

from ..config import Settings
from ..models import ApplyChannel, Job, RawJob
from ..store import Store

logger = logging.getLogger(__name__)

_EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")


def run_parse(settings: Settings, store: Store) -> int:
    """Parse all collected jobs. Returns the number parsed."""
    count = 0
    for raw in list(store.iter_raw_for_parse()):
        try:
            job = _parse(raw)
        except Exception as exc:  # noqa: BLE001
            logger.error("Parse failed for %s/%s: %s", raw.source, raw.external_id, exc)
            # Store a minimal record so it advances and isn't retried forever.
            job = Job(source=raw.source, external_id=raw.external_id, url=raw.url)
        store.save_parsed(job)
        count += 1
    logger.info("Parse: processed %d job(s)", count)
    return count


def _parse(raw: RawJob) -> Job:
    if raw.source == "greenhouse":
        return _parse_greenhouse(raw)
    if raw.source == "lever":
        return _parse_lever(raw)
    if raw.source == "ashby":
        return _parse_ashby(raw)
    if raw.source == "remotive":
        return _parse_remotive(raw)
    if raw.source == "rss":
        return _parse_rss(raw)
    if raw.source == "linkedin":
        return _parse_linkedin(raw)
    # Generic fallback: keep the URL, scan text for an email.
    return Job(
        source=raw.source,
        external_id=raw.external_id,
        url=raw.url,
        description=raw.raw_text[:20000],
        contact_email=_find_email(raw.raw_text),
    )


def _parse_greenhouse(raw: RawJob) -> Job:
    data = json.loads(raw.raw_text) if raw.raw_text else {}
    content_html = html.unescape(data.get("content", ""))
    description = BeautifulSoup(content_html, "html.parser").get_text("\n").strip()
    location = (data.get("location") or {}).get("name", "")
    company = _company_from_label(raw.portal_label)

    return Job(
        source=raw.source,
        external_id=raw.external_id,
        url=raw.url,
        title=data.get("title", ""),
        company=company,
        location=location,
        description=description,
        apply_link=data.get("absolute_url", raw.url),
        apply_channel=ApplyChannel.GREENHOUSE_FORM,
        contact_email=_find_email(description),
    )


def _parse_lever(raw: RawJob) -> Job:
    data = json.loads(raw.raw_text) if raw.raw_text else {}
    categories = data.get("categories") or {}
    description = data.get("descriptionPlain") or BeautifulSoup(
        data.get("description", ""), "html.parser"
    ).get_text("\n").strip()
    return Job(
        source=raw.source,
        external_id=raw.external_id,
        url=data.get("hostedUrl", raw.url),
        title=data.get("text", ""),
        company=_company_from_label(raw.portal_label),
        location=categories.get("location", ""),
        description=description,
        apply_link=data.get("applyUrl") or data.get("hostedUrl", raw.url),
        apply_channel=ApplyChannel.EXTERNAL_LINK,
        contact_email=_find_email(description),
    )


def _parse_ashby(raw: RawJob) -> Job:
    data = json.loads(raw.raw_text) if raw.raw_text else {}
    description = data.get("descriptionPlain") or BeautifulSoup(
        data.get("descriptionHtml", ""), "html.parser"
    ).get_text("\n").strip()
    return Job(
        source=raw.source,
        external_id=raw.external_id,
        url=data.get("jobUrl", raw.url),
        title=data.get("title", ""),
        company=_company_from_label(raw.portal_label),
        location=data.get("location", ""),
        description=description,
        apply_link=data.get("applyUrl") or data.get("jobUrl", raw.url),
        apply_channel=ApplyChannel.EXTERNAL_LINK,
        contact_email=_find_email(description),
    )


def _parse_remotive(raw: RawJob) -> Job:
    data = json.loads(raw.raw_text) if raw.raw_text else {}
    description = BeautifulSoup(data.get("description", ""), "html.parser").get_text("\n").strip()
    return Job(
        source=raw.source,
        external_id=raw.external_id,
        url=data.get("url", raw.url),
        title=data.get("title", ""),
        company=data.get("company_name", ""),
        location=data.get("candidate_required_location", ""),
        description=description,
        apply_link=data.get("url", raw.url),
        apply_channel=ApplyChannel.EXTERNAL_LINK,
        salary=data.get("salary", ""),
        remote="remote",
        posted_at=data.get("publication_date", ""),
        contact_email=_find_email(description),
    )


def _parse_rss(raw: RawJob) -> Job:
    data = json.loads(raw.raw_text) if raw.raw_text else {}
    description = BeautifulSoup(data.get("description_html", ""), "html.parser").get_text(
        "\n"
    ).strip()
    return Job(
        source=raw.source,
        external_id=raw.external_id,
        url=data.get("link", raw.url),
        title=data.get("title", ""),
        company=data.get("company", ""),
        location=data.get("location", ""),
        description=description,
        apply_link=data.get("link", raw.url),
        apply_channel=ApplyChannel.EXTERNAL_LINK,
        posted_at=data.get("published", ""),
        contact_email=_find_email(description),
    )


def _parse_linkedin(raw: RawJob) -> Job:
    soup = BeautifulSoup(raw.raw_text or "", "html.parser")
    title = _first_text(
        soup, [".top-card-layout__title", "h1.topcard__title", "h1"]
    )
    company = _first_text(
        soup, [".topcard__org-name-link", ".top-card-layout__card a", ".topcard__flavor"]
    )
    location = _first_text(
        soup, [".topcard__flavor--bullet", ".top-card-layout__second-subline"]
    )
    description = _first_text(
        soup, [".show-more-less-html__markup", ".description__text", ".jobs-description__content"]
    )

    return Job(
        source=raw.source,
        external_id=raw.external_id,
        url=raw.url,
        title=title,
        company=company,
        location=location,
        description=description,
        apply_link=raw.url,
        apply_channel=ApplyChannel.EXTERNAL_LINK,
        contact_email=_find_email(description),
    )


def _first_text(soup: BeautifulSoup, selectors: list[str]) -> str:
    for selector in selectors:
        el = soup.select_one(selector)
        if el:
            text = el.get_text(" ", strip=True)
            if text:
                return text
    return ""


def _find_email(text: Optional[str]) -> str:
    if not text:
        return ""
    match = _EMAIL_RE.search(text)
    return match.group(0) if match else ""


def _company_from_label(label: str) -> str:
    """Derive a company name from a ``"<source>:<company>"`` portal label."""
    return label.split(":", 1)[-1] if ":" in label else ""
