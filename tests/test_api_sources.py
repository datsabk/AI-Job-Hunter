"""Tests for the API-based source adapters (network / feedparser mocked)."""

import json
import sys
import types

from aijobhunter.sources import ashby as ashby_mod
from aijobhunter.sources import lever as lever_mod
from aijobhunter.sources import remotive as remotive_mod
from aijobhunter.sources.ashby import AshbySource
from aijobhunter.sources.lever import LeverSource
from aijobhunter.sources.remotive import RemotiveSource
from aijobhunter.sources.rss import RSSSource


class _Resp:
    def __init__(self, payload, status=200):
        self._payload = payload
        self.status_code = status

    def json(self):
        return self._payload


# ---- Remotive ----

def test_remotive_collect(monkeypatch):
    payload = {"jobs": [{"id": 7, "url": "http://r/7", "title": "Backend Eng",
                          "company_name": "Acme"}]}
    monkeypatch.setattr(remotive_mod.requests, "get", lambda *a, **k: _Resp(payload))
    raws = RemotiveSource().collect({"category": "software-dev"})
    assert len(raws) == 1
    assert raws[0].source == "remotive"
    assert json.loads(raws[0].raw_text)["company_name"] == "Acme"


# ---- Lever ----

def test_lever_collect_and_filter(monkeypatch):
    payload = [
        {"id": "a", "text": "Senior Backend Engineer", "hostedUrl": "http://l/a"},
        {"id": "b", "text": "Recruiter", "hostedUrl": "http://l/b"},
    ]
    monkeypatch.setattr(lever_mod.requests, "get", lambda *a, **k: _Resp(payload))
    raws = LeverSource().collect({"company": "acme", "title_includes": ["engineer"]})
    assert len(raws) == 1
    assert raws[0].external_id == "a"
    assert raws[0].portal_label == "lever:acme"


# ---- Ashby ----

def test_ashby_collect(monkeypatch):
    payload = {"jobs": [{"id": "x1", "title": "Platform Engineer",
                         "jobUrl": "http://a/x1", "location": "Remote"}]}
    monkeypatch.setattr(ashby_mod.requests, "get", lambda *a, **k: _Resp(payload))
    raws = AshbySource().collect({"company": "ramp"})
    assert len(raws) == 1
    assert raws[0].external_id == "x1"
    assert raws[0].portal_label == "ashby:ramp"


# ---- RSS (feedparser injected) ----

def _fake_feedparser(entries):
    mod = types.ModuleType("feedparser")
    mod.parse = lambda url: types.SimpleNamespace(entries=entries)
    return mod


def test_rss_collect_dedupes_and_splits(monkeypatch):
    entries = [
        types.SimpleNamespace(title="Senior SRE at Globex", link="http://f/1",
                              id="http://f/1", summary="<p>Ops</p>", published="2026-01-01",
                              author="Globex"),
        types.SimpleNamespace(title="Acme: Backend Engineer", link="http://f/2",
                              id="http://f/2", summary="APIs", published="", author=""),
        # duplicate id -> should be dropped
        types.SimpleNamespace(title="Dup", link="http://f/1", id="http://f/1",
                              summary="", published="", author=""),
    ]
    monkeypatch.setitem(sys.modules, "feedparser", _fake_feedparser(entries))
    raws = RSSSource().collect({"url": "http://feed", "label": "rss:test"})
    assert len(raws) == 2
    p0 = json.loads(raws[0].raw_text)
    assert p0["title"] == "Senior SRE" and p0["company"] == "Globex"
    p1 = json.loads(raws[1].raw_text)
    assert p1["title"] == "Backend Engineer" and p1["company"] == "Acme"
