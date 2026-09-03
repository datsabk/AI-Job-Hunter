"""Pydantic data models shared across all pipeline stages.

The pipeline moves a job through these shapes:

    RawJob   -> what a SourceAdapter collected (mostly unstructured)
    Job      -> structured fields extracted from the raw payload, plus the
                keyword-match result (score + matched keywords)
    JobScore -> an on-demand LLM fit assessment for a single Job
    ApplyDraft -> a ready-to-review application artifact

Bulk matching is purely keyword-based; ``JobScore`` and ``ApplyDraft`` are only
produced on demand, per job, from the TUI.

``PipelineStatus`` tracks how far a stored job has progressed so each stage can
pick up exactly the rows it still needs to process (making the pipeline
resumable).
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class PipelineStatus(str, Enum):
    """Where a stored job sits in the pipeline."""

    COLLECTED = "collected"
    PARSED = "parsed"
    FILTERED = "filtered"  # passed keyword filtering — kept
    REJECTED = "rejected"  # failed keyword filtering — excluded


class ApplyChannel(str, Enum):
    """How an application would be submitted."""

    EMAIL = "email"
    GREENHOUSE_FORM = "greenhouse_form"
    EXTERNAL_LINK = "external_link"  # fallback: just hand the user the link
    UNKNOWN = "unknown"


class RawJob(BaseModel):
    """Unstructured job payload as returned by a SourceAdapter."""

    source: str  # adapter name, e.g. "linkedin" / "greenhouse"
    external_id: str  # stable id within the source, used for dedupe
    url: str
    raw_text: str = ""  # HTML, JSON, or plain text — parser decides
    portal_label: str = ""  # human label for which portal entry produced this
    collected_at: datetime = Field(default_factory=_utcnow)


class Job(BaseModel):
    """Structured job details extracted from a RawJob."""

    source: str
    external_id: str
    url: str
    title: str = ""
    company: str = ""
    location: str = ""
    description: str = ""
    poster_name: str = ""
    poster_profile: str = ""
    contact_email: str = ""  # only when explicitly shown in the posting
    apply_link: str = ""
    apply_channel: ApplyChannel = ApplyChannel.UNKNOWN
    salary: str = ""
    remote: str = ""
    posted_at: str = ""
    # Keyword-match result (set by the filter stage).
    keyword_score: int = 0  # number of include-keyword hits
    matched_keywords: list[str] = Field(default_factory=list)


class JobScore(BaseModel):
    """An on-demand LLM fit assessment for a single Job."""

    fit_score: int = Field(ge=0, le=100)
    reason: str = ""
    recommended: bool = False


class ApplyDraft(BaseModel):
    """A ready-to-review application artifact produced by an ApplyAdapter."""

    channel: ApplyChannel
    target: str = ""  # email address or form URL
    subject: str = ""
    body: str = ""
    form_fields: dict[str, Any] = Field(default_factory=dict)
    attachments: list[str] = Field(default_factory=list)
    artifact_path: str = ""  # where the draft was written (e.g. an .eml file)
    notes: str = ""  # human guidance (e.g. "review before sending")
