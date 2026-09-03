"""Pipeline orchestrator.

The bulk pipeline is entirely keyword-based and never calls the LLM:
``collect → parse → filter → export`` (CSV). Fit assessment and drafting happen
on demand, per job, from the TUI (see ``aijobhunter/tui/``). Each stage persists
its progress, so the pipeline is resumable and stages can run independently.
"""

from __future__ import annotations

import logging
from typing import Any, Callable

from .config import Settings
from .stages import collect, export_csv, filter as filter_stage, parse
from .store import Store

logger = logging.getLogger(__name__)

# Canonical stage order. All keyword-based / offline — no LLM.
STAGE_ORDER = ["collect", "parse", "filter", "export"]


def run_pipeline(settings: Settings, stages: list[str]) -> dict[str, Any]:
    """Run the requested stages in canonical order. Returns a summary dict."""
    unknown = [s for s in stages if s not in STAGE_ORDER]
    if unknown:
        raise ValueError(f"Unknown stage(s): {unknown}. Valid: {STAGE_ORDER}")
    ordered = [s for s in STAGE_ORDER if s in stages]

    summary: dict[str, Any] = {}
    with Store(settings.db_path) as store:
        runners: dict[str, Callable[[], Any]] = {
            "collect": lambda: collect.run_collect(settings, store),
            "parse": lambda: parse.run_parse(settings, store),
            "filter": lambda: filter_stage.run_filter(settings, store),
            "export": lambda: export_csv.run_export_csv(settings, store),
        }
        for stage in ordered:
            logger.info("=== stage: %s ===", stage)
            summary[stage] = runners[stage]()
        summary["status_counts"] = store.counts_by_status()

    return summary
