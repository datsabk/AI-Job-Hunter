# Testing

Run the full suite from the project root (inside the venv):

```bash
source .venv/bin/activate
python -m pytest -q
```

All tests are **offline** — no network and no real LLM calls. Network
(`requests`) is monkeypatched and the AI client is replaced by an in-memory
`FakeAI` (see `tests/conftest.py`). Temp paths are used for the DB and output.

## Shared fixtures — `tests/conftest.py`

- `settings` — a `Settings` pointing at temp DB/output paths with test
  credentials; never touches real data.
- `fake_ai` — stand-in for an `LLMClient` returning scripted
  `generate`/`generate_json` responses (routes scoring vs enrichment prompts).
- `profile` — a sample candidate profile dict.

## Coverage by file

| File | What it covers |
|------|----------------|
| `test_models.py` | Model defaults, `JobScore` 0–100 bounds, `ApplyDraft` JSON round-trip, `PipelineStatus` values. |
| `test_store.py` | Dedupe on `(source, external_id)`; full COLLECTED→…→EXPORTED transition; draft/export threshold filtering. |
| `test_registry.py` | Resolving known adapters, error on unknown, registered adapter names. |
| `test_api_sources.py` | API adapters with mocked network/feedparser: Remotive, Lever (+title filter), Ashby collect; RSS dedupe + title/company splitting. |
| `test_greenhouse.py` | Greenhouse `collect()` with mocked HTTP: RawJob shape, `title_includes` filter, HTTP-error handling. |
| `test_parse.py` | Parsing Greenhouse/Lever/Ashby/Remotive/RSS JSON and LinkedIn HTML into `Job`; email extraction; safe handling of missing fields. |
| `test_ollama_client.py` | Ollama `generate`/`generate_json` (with `format:"json"`), payload shape, connection-refused and non-200 error handling. |
| `test_provider.py` | Provider factory builds the Ollama client. |
| `test_documents.py` | Resume extraction from txt/md/docx (incl. table cells), `.pdf` routing, missing-file error. |
| `test_enrich.py` | Enrich stage saves structured fields, is idempotent, uses an extraction (not scoring) prompt, and feeds enrichment into scoring. |
| `test_export_csv.py` | CSV export of all listed jobs: header/rows, comma escaping, scored jobs first, blank score fields for unscored jobs, custom path creation. |
| `test_pipeline_stages.py` | Integration: `score` → `draft` (Greenhouse adapter writes an artifact) → `export` (TXT dossier + `index.txt`). |

## Notes for future refactors

- Per the project guideline, create temporary tests around any refactor, run
  them, and clean them up afterward.
- The LinkedIn adapter (`aijobhunter/sources/linkedin.py`) is **not** unit-tested
  because it drives a real browser and a live, ToS-restricted site. Verify it
  manually in attended mode. Its parsing counterpart (`_parse_linkedin`) *is*
  covered by `test_parse.py` against static HTML.
