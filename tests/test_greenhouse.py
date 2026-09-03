"""Tests for the Greenhouse source adapter (network mocked)."""

import json

from aijobhunter.sources import greenhouse
from aijobhunter.sources.greenhouse import GreenhouseSource


class _FakeResp:
    def __init__(self, payload, status=200):
        self._payload = payload
        self.status_code = status

    def json(self):
        return self._payload


_BOARD = {
    "jobs": [
        {"id": 101, "title": "Senior Platform Engineer", "absolute_url": "http://gh/101",
         "location": {"name": "Remote"}, "content": "<p>Build stuff</p>"},
        {"id": 102, "title": "Marketing Lead", "absolute_url": "http://gh/102",
         "location": {"name": "NYC"}, "content": "<p>Ads</p>"},
    ]
}


def test_collect_returns_rawjobs(monkeypatch):
    monkeypatch.setattr(greenhouse.requests, "get", lambda *a, **k: _FakeResp(_BOARD))
    raws = GreenhouseSource().collect({"company": "acme"})
    assert len(raws) == 2
    assert raws[0].source == "greenhouse"
    assert raws[0].external_id == "101"
    assert json.loads(raws[0].raw_text)["title"] == "Senior Platform Engineer"
    assert raws[0].portal_label == "greenhouse:acme"


def test_collect_title_filter(monkeypatch):
    monkeypatch.setattr(greenhouse.requests, "get", lambda *a, **k: _FakeResp(_BOARD))
    raws = GreenhouseSource().collect({"company": "acme", "title_includes": ["engineer"]})
    assert len(raws) == 1
    assert raws[0].external_id == "101"


def test_collect_handles_http_error(monkeypatch):
    monkeypatch.setattr(greenhouse.requests, "get", lambda *a, **k: _FakeResp({}, status=404))
    assert GreenhouseSource().collect({"company": "acme"}) == []
