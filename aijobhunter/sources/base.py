"""Base contract for source adapters.

A SourceAdapter knows how to turn one portal config entry into a list of
``RawJob`` objects. Keeping this interface tiny is what makes the tool
multi-portal: adding a site means writing one ``collect`` method and registering
the class — no changes to the pipeline.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from ..models import RawJob


class SourceAdapter(ABC):
    """Collect raw jobs from a single configured portal entry."""

    #: Adapter name used in portals.yaml (``adapter: <name>``) and the registry.
    name: str = ""

    @abstractmethod
    def collect(self, config: dict[str, Any]) -> list[RawJob]:
        """Return raw jobs for the given portal config entry."""
        raise NotImplementedError
