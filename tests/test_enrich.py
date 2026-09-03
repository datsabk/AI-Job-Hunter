"""Tests for the enrich stage and its interaction with scoring."""

from aijobhunter.models import Job, RawJob
from aijobhunter.stages import enrich as enrich_stage
from aijobhunter.stages import score as score_stage
from aijobhunter.store import Store


def _seed_parsed(store: Store) -> Job:
    store.add_raw(RawJob(source="remotive", external_id="1", url="http://r/1"))
    job = Job(source="remotive", external_id="1", url="http://r/1",
              title="Backend Engineer", company="Acme",
              description="Build distributed systems in Python and Go.")
    store.save_parsed(job)
    return job


def test_enrich_saves_structured_fields(settings, fake_ai):
    with Store(settings.db_path) as store:
        _seed_parsed(store)
        n = enrich_stage.run_enrich(settings, store, fake_ai)
        assert n == 1

        enrichment = store.get_enrichment("remotive", "1")
        assert enrichment is not None
        assert "Python" in enrichment.skills
        assert enrichment.seniority == "senior"

        # Idempotent: already-enriched jobs are not re-processed.
        assert enrich_stage.run_enrich(settings, store, fake_ai) == 0


def test_enrich_prompt_is_extraction_not_scoring(settings, fake_ai):
    with Store(settings.db_path) as store:
        _seed_parsed(store)
        enrich_stage.run_enrich(settings, store, fake_ai)
    # The enrich prompt must ask for skills, not a fit score.
    assert any("skills" in p.lower() and "fit_score" not in p for p in fake_ai.json_calls)


def test_score_uses_enrichment_when_present(settings, fake_ai, profile):
    with Store(settings.db_path) as store:
        _seed_parsed(store)
        enrich_stage.run_enrich(settings, store, fake_ai)
        score_stage.run_score(settings, store, fake_ai, profile)

    # The scoring prompt should include the extracted structured facts.
    score_prompts = [p for p in fake_ai.json_calls if "fit_score" in p]
    assert score_prompts, "expected a scoring prompt"
    assert "structured facts" in score_prompts[-1].lower()
