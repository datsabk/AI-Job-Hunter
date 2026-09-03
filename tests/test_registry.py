"""Tests for the source adapter registry."""

import pytest

from aijobhunter.sources.greenhouse import GreenhouseSource
from aijobhunter.sources.registry import available_adapters, get_adapter


def test_get_known_adapter():
    adapter = get_adapter("greenhouse")
    assert isinstance(adapter, GreenhouseSource)


def test_unknown_adapter_raises():
    with pytest.raises(ValueError, match="Unknown source adapter"):
        get_adapter("does-not-exist")


def test_available_adapters_lists_registered():
    names = available_adapters()
    for expected in ["greenhouse", "linkedin", "lever", "ashby", "remotive", "rss"]:
        assert expected in names
