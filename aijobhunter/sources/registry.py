"""Registry mapping adapter names to SourceAdapter classes.

Import a new adapter here and add it to ``_ADAPTERS`` to make it usable from
portals.yaml. The LinkedIn adapter is imported lazily so that Playwright is only
required when someone actually enables it.
"""

from __future__ import annotations

from typing import Callable

from .ashby import AshbySource
from .base import SourceAdapter
from .greenhouse import GreenhouseSource
from .lever import LeverSource
from .remotive import RemotiveSource
from .rss import RSSSource


def _linkedin_factory() -> SourceAdapter:
    # Imported lazily: Playwright is only needed when LinkedIn is enabled.
    from .linkedin import LinkedInSource

    return LinkedInSource()


_ADAPTERS: dict[str, Callable[[], SourceAdapter]] = {
    GreenhouseSource.name: GreenhouseSource,
    LeverSource.name: LeverSource,
    AshbySource.name: AshbySource,
    RemotiveSource.name: RemotiveSource,
    RSSSource.name: RSSSource,
    "linkedin": _linkedin_factory,
}


def get_adapter(name: str) -> SourceAdapter:
    """Instantiate the adapter registered under ``name``."""
    try:
        factory = _ADAPTERS[name]
    except KeyError:
        known = ", ".join(sorted(_ADAPTERS))
        raise ValueError(f"Unknown source adapter '{name}'. Known adapters: {known}")
    return factory()


def available_adapters() -> list[str]:
    return sorted(_ADAPTERS)
