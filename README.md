<div align="center">

# 🎯 AI Job Hunter

**Find the right jobs without melting your laptop — keyword-first, local, and private.**

A pluggable, multi-portal job-discovery engine. It pulls postings from public
APIs and feeds, filters them **purely by keywords** derived from your résumé (no
LLM in bulk), and hands you a ranked CSV plus a **terminal UI** where you can
assess fit or draft an application **one job at a time, on demand** — all powered
by a **local LLM (Ollama)**.

[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![LLM: Ollama](https://img.shields.io/badge/LLM-Ollama%20(local)-black.svg)](https://ollama.com)
[![TUI: Textual](https://img.shields.io/badge/TUI-Textual-5a2ca0.svg)](https://textual.textualize.io)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-orange.svg)](#-contributing)

</div>

---

> 🔒 **100% local & private.** Your résumé and the jobs you look at never leave
> your machine. No API keys, no cloud, no cost.
>
> ⚡ **Light on your machine.** Bulk matching is pure keyword filtering — the LLM
> runs only when *you* ask it to, on a single job.

## 📑 Table of Contents

- [Why AI Job Hunter?](#-why-ai-job-hunter)
- [How it works](#-how-it-works)
- [Requirements](#-requirements)
- [Quick start](#-quick-start)
- [Configuration](#-configuration)
- [Usage](#-usage)
- [The terminal UI](#-the-terminal-ui)
- [Output](#-output)
- [Project structure](#-project-structure)
- [Extending it](#-extending-it)
- [Testing](#-testing)
- [Roadmap](#-roadmap)
- [Responsible use](#-responsible-use)
- [Contributing](#-contributing) · [License](#-license)

## 🤔 Why AI Job Hunter?

Job hunting is a grind: the same searches across a dozen boards, skimming
hundreds of descriptions, rewriting the same cover letter. AI Job Hunter
automates the tedious parts while keeping you in control — and, crucially, keeps
the expensive AI work **on demand** so it never pins your CPU running an LLM over
hundreds of jobs you'll never apply to.

The flow is deliberately staged:

1. **Extract keywords** from your résumé (one LLM call), then you edit them and
   add exclusions.
2. **Collect & filter** jobs by those keywords — fast, deterministic, no LLM.
3. **Browse** the results in a TUI and spend AI only where it matters: *assess
   fit* or *draft an application* for a specific job.

## 🛠 How it works

```
  ┌──────────┐        ┌─────────────────────── run (no LLM) ───────────────────────┐
  │ keywords │        │  collect  →  parse  →  filter (keyword)  →  export (CSV)     │
  │ (1 LLM   │───────▶│  sources     structe    keep/reject +        ranked          │
  │  call +  │  saves │              -ured      keyword_score        spreadsheet     │
  │  your    │  incl/ └─────────────────────────────────────────────────────────────┘
  │  edits)  │  excl                              │
  └──────────┘                                    ▼
                                        ┌──────────────────┐   on demand, per job:
                                        │   browse (TUI)    │──▶  f = assess fit  (LLM)
                                        │  ranked job table │──▶  d = draft app   (LLM)
                                        └──────────────────┘
```

- **Bulk pipeline is keyword-only.** `collect → parse → filter → export` never
  calls the LLM. Filtering keeps a job if it hits ≥1 include keyword and 0
  exclude keywords, and ranks by hit count (`keyword_score`).
- **The LLM is on demand.** Fit assessment and drafting happen per job, from the
  TUI — never in bulk.
- **Source adapters** (`aijobhunter/sources/`) decide *where jobs come from*;
  **apply adapters** (`aijobhunter/apply/`) decide *how a draft is prepared*.

## 📦 Requirements

- **Python 3.10+**
- **[Ollama](https://ollama.com)** running locally with a model pulled
  (default `llama3`)
- *(optional)* **Chromium via Playwright** — only for the LinkedIn adapter

## 🚀 Quick start

```bash
# 1. Clone & install
git clone https://github.com/datsabk/AI-Job-Hunter.git
cd AI-Job-Hunter
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 2. Start Ollama (in another terminal)
ollama pull llama3 && ollama serve

# 3. Create your config from the samples
cp env.example .env
cp config/portals.example.yaml config/portals.yaml
cp config/profile.example.yaml config/profile.yaml   # point resume_file at your CV (.pdf/.docx/.md/.txt)

# 4. Extract keywords from your résumé (interactive: edit + add exclusions)
python -m aijobhunter keywords

# 5. Collect, keyword-filter, and write the CSV (no LLM, fast)
python -m aijobhunter run

# 6. Browse results; assess fit / draft applications on demand
python -m aijobhunter browse
```

No API keys, no accounts. Everything lands in `./output/`.

> 💡 The LinkedIn adapter is the only source needing a browser. If you enable it,
> also run `python -m playwright install chromium`.

## ⚙️ Configuration

### Sources — `config/portals.yaml`

| Adapter | Kind | Needs | Notes |
|---|---|---|---|
| `greenhouse` | Public JSON API | `company` board token | No browser, low risk |
| `lever` | Public JSON API | `company` board token | No browser |
| `ashby` | Public JSON API | `company` board token | No browser |
| `remotive` | Public JSON API | `category`, `search`, `limit` | Remote jobs |
| `rss` | RSS/Atom feeds | `feeds: [{url, label}]` | Any job feed |
| `linkedin` | Browser (Playwright) | `urls`, caps | ⚠️ opt-in, attended, ToS risk |

#### LinkedIn — using your logged-in Chrome

LinkedIn needs a browser with your session. On **Chrome ≥ 136** you can't let a
tool launch your everyday profile: Chrome refuses automation on the default
user-data dir, and a tool-launched Chrome sets `navigator.webdriver`, which trips
the *"this browser may not be secure"* check. So instead, **you launch Chrome and
the hunter attaches to it** over the DevTools protocol.

One-time setup — fully quit Chrome, then run:

```bash
"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
  --remote-debugging-port=9222 \
  --user-data-dir="$HOME/.li-br-chrome"
```

Log into LinkedIn in that window (it's a normal browser — no bot detection), keep
it open, and set in `portals.yaml`:

```yaml
- adapter: linkedin
  enabled: true
  urls: [ ... ]
  connect_cdp: true      # attach instead of launch
  cdp_port: 9222         # matches --remote-debugging-port above
```

The window and its login persist between runs. (The legacy `use_real_chrome`
mode still exists but is broken on Chrome ≥ 136 — prefer `connect_cdp`.)

### Keywords — `config/keywords.yaml`

Usually generated by `aijobhunter keywords`, but you can hand-edit it. Matching
is case-insensitive substring matching over title + company + location +
description.

```yaml
include:            # keep a job if it matches AT LEAST ONE
  - platform engineer
  - kubernetes
  - python
exclude:            # reject a job if it matches ANY (wins over include)
  - intern
  - clearance required
```

### Profile — `config/profile.yaml`

```yaml
name: Your Name
email: you@example.com
objective: "Senior backend / platform roles, remote-first."
resume_file: /path/to/your/CV.pdf   # .pdf / .docx / .md / .txt — auto-extracted
```

### Environment — `.env`

| Variable | Default | Purpose |
|---|---|---|
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama server URL |
| `OLLAMA_MODEL` | `llama3` | Model for keyword extraction + on-demand actions |
| `LLM_TEMPERATURE` | `0.2` | Sampling temperature |
| `AIJOBHUNTER_DB_PATH` | `./data/aijobhunter.db` | SQLite store |
| `AIJOBHUNTER_OUTPUT_DIR` | `./output` | Where CSV/drafts are written |
| `AIJOBHUNTER_SCORE_THRESHOLD` | `70` | Fit score marked "recommended" at/above this |
| `AIJOBHUNTER_BATCH_SIZE` | `5` | Max jobs a batch TUI action processes |
| `AIJOBHUNTER_PORTALS_CONFIG` | `./config/portals.yaml` | Portals config path |
| `AIJOBHUNTER_PROFILE_CONFIG` | `./config/profile.yaml` | Profile config path |
| `AIJOBHUNTER_KEYWORDS_CONFIG` | `./config/keywords.yaml` | Keywords config path |

## 💻 Usage

```bash
python -m aijobhunter keywords          # extract keywords from résumé (interactive)
python -m aijobhunter run               # collect → parse → filter → CSV (no LLM)
python -m aijobhunter run --stages collect,parse,filter
python -m aijobhunter browse            # TUI: assess fit / draft on demand
python -m aijobhunter export-csv [path|-]
python -m aijobhunter status            # jobs per pipeline stage
python -m aijobhunter -v run            # verbose logging
```

## 🖥 The terminal UI

`aijobhunter browse` opens a Textual table of your kept jobs, ranked by keyword
score.

| Key | Action |
|---|---|
| `↑` / `↓` | Move the cursor |
| `space` | Select / deselect a row |
| `f` | **Assess fit** of the current (or selected) job — LLM scores 0–100 + reason |
| `d` | **Draft** an application for the current (or selected) job |
| `b` | Run assess-fit on all selected rows (up to `AIJOBHUNTER_BATCH_SIZE`) |
| `o` | Show job detail (description, matched keywords, fit, draft) |
| `q` | Quit |

LLM actions run in a background thread, so the UI stays responsive.

## 📤 Output

- `output/jobs.csv` — every kept job, ranked by `keyword_score`, with
  `matched_keywords`; `fit_score`/`fit_reason`/`drafted` fill in as you act.
- `output/drafts/*.eml` / `*.json` — reviewable application drafts (never sent).

## 🗂 Project structure

```
AI-Job-Hunter/
├── aijobhunter/
│   ├── cli.py                # CLI (keywords / run / browse / status / export-csv)
│   ├── config.py             # env Settings + YAML loaders (portals/profile/keywords)
│   ├── documents.py          # résumé text extraction (txt/md/pdf/docx)
│   ├── models.py             # pydantic models
│   ├── store.py              # SQLite store; dedupe + status transitions
│   ├── pipeline.py           # keyword-only pipeline: collect→parse→filter→export
│   ├── ai/                   # LLMClient protocol, Ollama client, provider factory
│   ├── sources/              # WHERE jobs come from (greenhouse/lever/ashby/remotive/rss/linkedin)
│   ├── apply/                # HOW a draft is prepared (email/greenhouse)
│   ├── stages/
│   │   ├── collect.py        # run each portal's adapter, store new jobs
│   │   ├── parse.py          # raw payload → structured Job
│   │   ├── keywords.py       # LLM keyword extraction from résumé
│   │   ├── filter.py         # keyword include/exclude + keyword_score (no LLM)
│   │   ├── score.py          # on-demand single-job fit assessment (LLM)
│   │   ├── draft.py          # on-demand single-job application draft (LLM)
│   │   └── export_csv.py     # write kept jobs to CSV
│   └── tui/                  # Textual app (app.py) + tested action logic (actions.py)
├── config/                   # *.example.yaml templates (your real configs are gitignored)
├── tests/                    # pytest suite (see TESTING.md)
├── requirements.txt · env.example · LICENSE · README.md
```

## 🧩 Extending it

**Add a job source:** create `aijobhunter/sources/<name>.py` with a
`SourceAdapter` subclass whose `collect(config)` returns `RawJob`s, register it
in `sources/registry.py`, add a parse branch in `stages/parse.py`, and add an
entry to `config/portals.yaml`.

**Add an apply channel:** create an adapter in `aijobhunter/apply/` implementing
`can_handle` / `prepare`, and add it to the list in `stages/draft.py`.

## 🧪 Testing

```bash
source .venv/bin/activate
python -m pytest -q
```

All tests are **offline** — network and LLM calls are mocked. The Textual app is
a thin shell over the tested `tui/actions.py`. See [TESTING.md](TESTING.md).

## 🗺 Roadmap

- [ ] Résumé → structured criteria for smarter keyword suggestions
- [ ] More apply adapters (Lever/Ashby form submission)
- [ ] Saved views / tagging in the TUI
- [ ] Scheduled collect with a daily digest

## ⚖️ Responsible use

- Applications are **prepared for review, never auto-sent**.
- The **LinkedIn adapter automates your own logged-in browser**; LinkedIn's Terms
  prohibit automation. It's **disabled by default**, runs **attended** (visible,
  capped, human-like pacing). Prefer the public-API sources.
- Respect each site's Terms of Service and rate limits.

## 🤝 Contributing

Contributions welcome! Open an issue to discuss significant changes first, keep
modules small and focused, add tests for new behaviour, and run
`python -m pytest` before opening a PR.

## 📄 License

Released under the [MIT License](LICENSE) © 2026 Abhishek Kothari.
