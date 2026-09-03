<div align="center">

# 🎯 AI Job Hunter

**Find the right jobs while you sleep — locally, privately, and for free.**

A pluggable, multi-portal job–discovery engine that pulls postings from public
APIs and feeds, uses a **local LLM (Ollama)** to extract structured facts and
score every role against *your* résumé, and drafts tailored applications for the
strong matches — then hands you a clean dossier and a spreadsheet to review.

[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![LLM: Ollama](https://img.shields.io/badge/LLM-Ollama%20(local)-black.svg)](https://ollama.com)
[![Tests](https://img.shields.io/badge/tests-45%20passing-brightgreen.svg)](TESTING.md)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-orange.svg)](#-contributing)

</div>

---

> 🔒 **100% local & private.** Your résumé and the jobs you look at never leave
> your machine — all AI runs on your own Ollama server. No API keys, no cloud, no cost.

## 📑 Table of Contents

- [Why AI Job Hunter?](#-why-ai-job-hunter)
- [Features](#-features)
- [How it works](#-how-it-works)
- [Requirements](#-requirements)
- [Quick start](#-quick-start)
- [Configuration](#-configuration)
- [Usage](#-usage)
- [Output](#-output)
- [Project structure](#-project-structure)
- [Extending it](#-extending-it)
- [Testing](#-testing)
- [Roadmap](#-roadmap)
- [Responsible use](#-responsible-use)
- [Contributing](#-contributing)
- [License](#-license)

## 🤔 Why AI Job Hunter?

Job hunting is a grind: the same searches across a dozen boards, skimming
hundreds of descriptions, and rewriting the same cover letter. AI Job Hunter
automates the tedious 80% so you can spend your time on the decisions that
matter — **which** roles to pursue and **what** to say.

It's built on two ideas:

1. **Sourcing should be pluggable.** Jobs live everywhere. Adding a new portal
   is one small class — no rewrites.
2. **AI should be local.** Scoring your résumé against a job is exactly the kind
   of private task that belongs on your own machine, not a paid API.

## ✨ Features

- 🔌 **Multi-portal sourcing** — Greenhouse, Lever, Ashby, Remotive, any RSS/Atom
  job feed, plus optional LinkedIn (browser, opt-in).
- 🧠 **Local LLM intelligence** — Ollama (`llama3`) extracts structured facts
  (skills, seniority, must-haves, comp, remote mode) and scores each role
  against your résumé.
- 📄 **Reads your real résumé** — `.txt`, `.md`, `.pdf`, or `.docx`.
- ✍️ **Drafts applications** — tailored email (`.eml`) or Greenhouse form fields,
  **prepared for review, never auto-sent**.
- 🗂️ **Clean outputs** — a TXT dossier per role, a ranked `index.txt`, and a
  full **CSV export**.
- ♻️ **Resumable pipeline** — SQLite-backed; run stages independently and pick up
  where you left off.
- 🧪 **Well tested** — 45 offline unit/integration tests.

## 🛠 How it works

A resumable six-stage pipeline backed by SQLite. Each stage reads rows at its
input status, does its work, and advances them — so you can run part of it now
and the rest later.

```
   ┌─────────┐   ┌────────┐   ┌────────────┐   ┌────────────┐   ┌──────────────────┐   ┌─────────────────┐
   │ collect │──▶│ parse  │──▶│   enrich   │──▶│   score    │──▶│      draft       │──▶│     export      │
   └─────────┘   └────────┘   └────────────┘   └────────────┘   └──────────────────┘   └─────────────────┘
   pluggable      raw payload   LLM extracts     LLM fit-scores    email / greenhouse     TXT dossiers +
   sources        → structured  structured facts vs your résumé    application drafts     index + CSV
```

- **Source adapters** (`aijobhunter/sources/`) decide *where jobs come from*.
- **Apply adapters** (`aijobhunter/apply/`) decide *how an application is prepared*,
  favouring channels that need no login (email drafts, Greenhouse forms).

## 📦 Requirements

- **Python 3.10+**
- **[Ollama](https://ollama.com)** running locally with a model pulled
  (default `llama3`)
- *(optional)* **Chromium via Playwright** — only if you enable the LinkedIn adapter

## 🚀 Quick start

```bash
# 1. Clone
git clone https://github.com/datsabk/AI-Job-Hunter.git
cd AI-Job-Hunter

# 2. Create a virtualenv and install deps
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 3. Start Ollama and pull the model (in another terminal)
ollama pull llama3
ollama serve

# 4. Create your config from the samples
cp env.example .env
cp config/portals.example.yaml config/portals.yaml
cp config/profile.example.yaml config/profile.yaml

# 5. Edit config/profile.yaml — point resume_file at your CV (.pdf/.docx/.md/.txt)
#    and set your objective. Edit config/portals.yaml to choose sources.

# 6. Run the pipeline
python -m aijobhunter run

# 7. Export a spreadsheet of everything found
python -m aijobhunter export-csv
```

That's it — no API keys, no accounts. Results appear in `./output/`.

> 💡 The LinkedIn adapter is the only source needing a browser. If you enable it,
> also run `python -m playwright install chromium`.

## ⚙️ Configuration

### Sources — `config/portals.yaml`

Each entry names an `adapter` and its settings. Enable as many as you like.

| Adapter | Kind | Needs | Notes |
|---|---|---|---|
| `greenhouse` | Public JSON API | `company` board token | No browser, low risk |
| `lever` | Public JSON API | `company` board token | No browser |
| `ashby` | Public JSON API | `company` board token | No browser |
| `remotive` | Public JSON API | `category`, `search`, `limit` | Remote jobs |
| `rss` | RSS/Atom feeds | `feeds: [{url, label}]` | Any job feed |
| `linkedin` | Browser (Playwright) | `urls`, caps | ⚠️ opt-in, attended, ToS risk |

```yaml
portals:
  - adapter: greenhouse
    enabled: true
    company: stripe
    title_includes: ["engineer"]   # optional case-insensitive title filter

  - adapter: remotive
    enabled: false
    category: software-dev
    search: platform engineer
    limit: 50
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
| `OLLAMA_MODEL` | `llama3` | Model used for enrich/score/draft |
| `LLM_TEMPERATURE` | `0.2` | Sampling temperature |
| `AIJOBHUNTER_DB_PATH` | `./data/aijobhunter.db` | SQLite store |
| `AIJOBHUNTER_OUTPUT_DIR` | `./output` | Where dossiers/CSV are written |
| `AIJOBHUNTER_SCORE_THRESHOLD` | `70` | Min fit score (0–100) to draft/export |
| `AIJOBHUNTER_PORTALS_CONFIG` | `./config/portals.yaml` | Portals config path |
| `AIJOBHUNTER_PROFILE_CONFIG` | `./config/profile.yaml` | Profile config path |
| `AIJOBHUNTER_BROWSER_PROFILE_DIR` | `./data/browser-profile` | LinkedIn browser profile |

## 💻 Usage

```bash
python -m aijobhunter run                              # full pipeline (collect..export)
python -m aijobhunter run --stages collect,parse,enrich
python -m aijobhunter run --stages score,draft,export
python -m aijobhunter status                           # jobs per pipeline stage
python -m aijobhunter export-csv [path|-]              # export listing to CSV (or stdout)
python -m aijobhunter -v run                           # verbose / debug logging
```

Because the pipeline is resumable, running `collect,parse,enrich` and then
`score,draft,export` later behaves identically to running all six at once.

> ⏱️ **Performance note:** `enrich` and `score` call the LLM **once per job**, so
> a large collect can be slow on a local model. Start with one source (or a
> `title_includes` filter / a Remotive `limit`) to gauge throughput.

## 📤 Output

Everything lands in `./output/`:

- `output/jobs/*.txt` — a dossier per relevant role: full details, contact email,
  apply link, fit score + reasoning, and the prepared draft.
- `output/drafts/*.eml` / `*.json` — reviewable application drafts.
- `output/index.txt` — all relevant roles ranked by fit score.
- `output/jobs.csv` — spreadsheet of every listed job (skills, seniority, remote
  mode, score, links, …).

## 🗂 Project structure

```
AI-Job-Hunter/
├── aijobhunter/
│   ├── cli.py                # CLI (run / status / export-csv)
│   ├── config.py             # env Settings + YAML loaders (dotenv)
│   ├── documents.py          # résumé text extraction (txt/md/pdf/docx)
│   ├── models.py             # pydantic models
│   ├── store.py              # SQLite store; dedupe + stage transitions
│   ├── pipeline.py           # orchestrates stages over a shared store/LLM
│   ├── ai/                   # LLMClient protocol, Ollama client, provider factory
│   ├── sources/              # WHERE jobs come from (greenhouse/lever/ashby/…)
│   ├── apply/                # HOW an application is prepared (email/greenhouse)
│   └── stages/               # collect → parse → enrich → score → draft → export
├── config/                   # portals + profile YAML (with *.example.yaml samples)
├── tests/                    # pytest suite (see TESTING.md)
├── requirements.txt
├── env.example
├── LICENSE
└── README.md
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

All tests are **offline** — network and LLM calls are mocked. See
[TESTING.md](TESTING.md) for per-file coverage.

## 🗺 Roadmap

- [ ] Concurrency / rate-limit knob for the LLM stages
- [ ] More apply adapters (Lever, Ashby form submission)
- [ ] Structured résumé → criteria extraction for even sharper scoring
- [ ] Scheduled/unattended runs with a daily digest

## ⚖️ Responsible use

- Applications are **prepared for review, never auto-sent**. You decide what goes
  out under your name.
- The **LinkedIn adapter automates your own logged-in browser**. LinkedIn's Terms
  prohibit automation and aggressive use can get an account restricted. It is
  **disabled by default**, runs **attended** (visible browser, hard time/volume
  caps, human-like pacing), and should be used at your own discretion. The
  public-API sources (Greenhouse/Lever/Ashby/Remotive/RSS) are the recommended
  default.
- Respect each site's Terms of Service and rate limits.

## 🤝 Contributing

Contributions are welcome! Please open an issue to discuss significant changes
first. Keep the codebase style (small, focused modules), add tests for new
behaviour, and run `python -m pytest` before opening a PR.

## 📄 License

Released under the [MIT License](LICENSE) © 2026 Abhishek Kothari.
