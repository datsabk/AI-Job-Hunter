"""Collect stage: run each configured portal's adapter and store new jobs."""

from __future__ import annotations

import logging
from typing import Any

from ..config import Settings, load_portals
from ..sources.registry import get_adapter
from ..store import Store

logger = logging.getLogger(__name__)


def run_collect(settings: Settings, store: Store) -> dict[str, int]:
    """Collect from every enabled portal. Returns per-portal new-job counts."""
    portals = load_portals(settings)
    stats: dict[str, int] = {}

    for entry in portals:
        adapter_name = entry.get("adapter")
        if not adapter_name:
            logger.warning("Skipping portal entry with no 'adapter': %s", entry)
            continue

        label = entry.get("label", adapter_name)
        try:
            adapter = get_adapter(adapter_name)
            raws = adapter.collect(entry)
        except Exception as exc:  # noqa: BLE001 - one portal failing must not kill the run
            logger.error("Collect failed for portal '%s': %s", label, exc)
            stats[label] = 0
            continue

        new_count = sum(1 for raw in raws if store.add_raw(raw))
        stats[label] = new_count
        logger.info("Collect: '%s' -> %d new job(s) (%d seen)", label, new_count, len(raws))

    return stats
