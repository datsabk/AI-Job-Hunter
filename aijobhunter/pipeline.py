"""Pipeline orchestrator.

Wires the stages together over a shared store, LLM client, and profile. Stages
run in a fixed order; the caller chooses which subset to run. Because each stage
persists its progress, running ``collect,parse,enrich`` now and
``score,draft,export`` later works exactly the same as running all at once.
"""

from __future__ import annotations

import logging
from typing import Any, Callable

from .ai.provider import build_llm_client
from .config import Settings, load_profile
from .stages import collect, draft, enrich, export, parse, score
from .store import Store

logger = logging.getLogger(__name__)

# Canonical stage order.
STAGE_ORDER = ["collect", "parse", "enrich", "score", "draft", "export"]

# Stages that need the LLM client and/or profile.
_NEEDS_AI = {"enrich", "score", "draft"}
_NEEDS_PROFILE = {"score", "draft"}


def run_pipeline(settings: Settings, stages: list[str]) -> dict[str, Any]:
    """Run the requested stages in canonical order. Returns a summary dict."""
    unknown = [s for s in stages if s not in STAGE_ORDER]
    if unknown:
        raise ValueError(f"Unknown stage(s): {unknown}. Valid: {STAGE_ORDER}")
    ordered = [s for s in STAGE_ORDER if s in stages]

    ai = build_llm_client(settings) if _NEEDS_AI & set(ordered) else None
    profile = load_profile(settings) if _NEEDS_PROFILE & set(ordered) else {}

    summary: dict[str, Any] = {}
    with Store(settings.db_path) as store:
        runners: dict[str, Callable[[], Any]] = {
            "collect": lambda: collect.run_collect(settings, store),
            "parse": lambda: parse.run_parse(settings, store),
            "enrich": lambda: enrich.run_enrich(settings, store, ai),
            "score": lambda: score.run_score(settings, store, ai, profile),
            "draft": lambda: draft.run_draft(settings, store, ai, profile),
            "export": lambda: export.run_export(settings, store),
        }
        for stage in ordered:
            logger.info("=== stage: %s ===", stage)
            summary[stage] = runners[stage]()
        summary["status_counts"] = store.counts_by_status()

    return summary
