# Testing

Run the full suite from the project root (inside the venv):

```bash
source .venv/bin/activate
python -m pytest -q
```

All tests are **offline** — no network and no real LLM calls. Network
(`requests` / `feedparser`) is monkeypatched and the LLM client is replaced by an
in-memory `FakeAI` (see `tests/conftest.py`). Temp paths are used for the DB,
output, and keywords config.

## Shared fixtures — `tests/conftest.py`

- `settings` — a `Settings` pointing at temp DB/output/keywords paths; never
  touches real data.
- `fake_ai` — stand-in for an `LLMClient`. `generate_json` routes on the prompt:
  keyword-extraction prompts get a keyword list; fit-assessment prompts get a
  score. `generate` returns draft text.
- `profile` — a sample candidate profile dict.

## Coverage by file

| File | What it covers |
|------|----------------|
| `test_models.py` | Model defaults incl. `Job.keyword_score`/`matched_keywords`, `JobScore` 0–100 bounds, `ApplyDraft` round-trip, `PipelineStatus` = {collected, parsed, filtered, rejected}. |
| `test_store.py` | Dedupe; parse→filter (kept/rejected) transitions; on-demand `save_score`/`save_draft` do **not** change status; `get_job`. |
| `test_registry.py` | Resolving known adapters, error on unknown, registered adapter names. |
| `test_api_sources.py` | Remotive/Lever/Ashby collect + RSS dedupe/splitting (network & feedparser mocked). |
| `test_greenhouse.py` | Greenhouse `collect()` with mocked HTTP. |
| `test_parse.py` | Parsing Greenhouse/Lever/Ashby/Remotive/RSS + LinkedIn HTML into `Job`; email scan; missing-field safety. |
| `test_documents.py` | Résumé extraction from txt/md/docx (incl. tables), `.pdf` routing, missing-file error. |
| `test_ollama_client.py` | Ollama `generate`/`generate_json` (with `format:"json"`), payload shape, connection/non-200 errors. |
| `test_provider.py` | Provider factory builds the Ollama client. |
| `test_keywords.py` | Résumé keyword extraction (dedupe/limit/bad-response) and keywords-config load/save round-trip. |
| `test_filter.py` | `match_job` keep/reject/rank logic; `run_filter` transitions and the no-keywords error. |
| `test_actions.py` | On-demand `assess_fit` (persists score) and `draft_application` (persists draft + writes artifact). |
| `test_export_csv.py` | CSV of kept jobs ranked by `keyword_score`, comma escaping, blank LLM columns until acted on, rejected jobs excluded. |
| `test_pipeline_stages.py` | Integration: `parse → filter → export` keeps only keyword-matching, non-excluded jobs and writes the CSV. |

## Notes for future refactors

- Per the project guideline, create temporary tests around any refactor, run
  them, and clean them up afterward.
- The Textual app (`aijobhunter/tui/app.py`) is a thin shell and is **not**
  unit-tested; its logic lives in `aijobhunter/tui/actions.py`, which **is**
  covered by `test_actions.py`.
- The LinkedIn adapter (`aijobhunter/sources/linkedin.py`) is **not** unit-tested
  because it drives a real browser and a live, ToS-restricted site; its parser
  (`_parse_linkedin`) *is* covered by `test_parse.py` against static HTML.
