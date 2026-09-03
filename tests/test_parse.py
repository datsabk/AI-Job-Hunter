"""Tests for the parse stage (Greenhouse JSON + LinkedIn HTML + email scan)."""

import json

from aijobhunter.models import ApplyChannel, RawJob
from aijobhunter.stages.parse import _parse


def test_parse_greenhouse():
    payload = {
        "title": "Backend Engineer",
        "absolute_url": "http://gh/101",
        "location": {"name": "Remote"},
        "content": "<p>Work on APIs. Reach us at jobs@acme.com</p>",
    }
    raw = RawJob(
        source="greenhouse", external_id="101", url="http://gh/101",
        raw_text=json.dumps(payload), portal_label="greenhouse:acme",
    )
    job = _parse(raw)
    assert job.title == "Backend Engineer"
    assert job.company == "acme"
    assert job.location == "Remote"
    assert "Work on APIs" in job.description
    assert job.apply_channel is ApplyChannel.GREENHOUSE_FORM
    assert job.contact_email == "jobs@acme.com"


def test_parse_linkedin_html():
    html = """
    <html><body>
      <h1 class="top-card-layout__title">Staff Engineer</h1>
      <a class="topcard__org-name-link">Globex</a>
      <span class="topcard__flavor--bullet">Berlin, Germany</span>
      <div class="show-more-less-html__markup">Lead the platform team.</div>
    </body></html>
    """
    raw = RawJob(source="linkedin", external_id="55", url="http://li/55", raw_text=html)
    job = _parse(raw)
    assert job.title == "Staff Engineer"
    assert job.company == "Globex"
    assert "Berlin" in job.location
    assert "Lead the platform team" in job.description
    assert job.apply_channel is ApplyChannel.EXTERNAL_LINK


def test_parse_greenhouse_missing_fields_is_safe():
    raw = RawJob(source="greenhouse", external_id="9", url="http://gh/9", raw_text="{}")
    job = _parse(raw)
    assert job.external_id == "9"
    assert job.title == ""


def test_parse_lever():
    payload = {
        "id": "a", "text": "Backend Engineer", "hostedUrl": "http://l/a",
        "applyUrl": "http://l/a/apply", "categories": {"location": "Remote"},
        "descriptionPlain": "Build services.",
    }
    raw = RawJob(source="lever", external_id="a", url="http://l/a",
                 raw_text=json.dumps(payload), portal_label="lever:netflix")
    job = _parse(raw)
    assert job.title == "Backend Engineer"
    assert job.company == "netflix"
    assert job.location == "Remote"
    assert job.apply_link == "http://l/a/apply"


def test_parse_ashby():
    payload = {"id": "x1", "title": "Platform Engineer", "jobUrl": "http://a/x1",
               "location": "Remote", "descriptionPlain": "Own the platform."}
    raw = RawJob(source="ashby", external_id="x1", url="http://a/x1",
                 raw_text=json.dumps(payload), portal_label="ashby:ramp")
    job = _parse(raw)
    assert job.title == "Platform Engineer"
    assert job.company == "ramp"
    assert "platform" in job.description.lower()


def test_parse_remotive():
    payload = {"id": 7, "url": "http://r/7", "title": "SRE", "company_name": "Acme",
               "candidate_required_location": "Worldwide",
               "description": "<p>Keep it up</p>", "salary": "$150k",
               "publication_date": "2026-02-01"}
    raw = RawJob(source="remotive", external_id="7", url="http://r/7",
                 raw_text=json.dumps(payload))
    job = _parse(raw)
    assert job.company == "Acme"
    assert job.location == "Worldwide"
    assert job.salary == "$150k"
    assert job.remote == "remote"


def test_parse_rss():
    payload = {"title": "Backend Engineer", "company": "Globex", "location": "",
               "description_html": "<p>APIs</p>", "link": "http://f/1",
               "published": "2026-01-01"}
    raw = RawJob(source="rss", external_id="http://f/1", url="http://f/1",
                 raw_text=json.dumps(payload), portal_label="rss:test")
    job = _parse(raw)
    assert job.title == "Backend Engineer"
    assert job.company == "Globex"
    assert "APIs" in job.description
    assert job.posted_at == "2026-01-01"
