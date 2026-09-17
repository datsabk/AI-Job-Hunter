"""Textual TUI: browse keyword-filtered jobs; assess fit / draft on demand.

This is a thin shell over ``aijobhunter.tui.actions`` (the tested logic). The LLM
is only ever called when you press ``f`` (assess fit) or ``d`` (draft) on a job
you selected — never in bulk.

Keys: ↑/↓ move · space select · f assess fit · d draft · b batch on selected
      o open/refresh detail · q quit
"""

from __future__ import annotations

from typing import Any, Optional

from ..ai.base import LLMClient
from ..ai.provider import build_llm_client
from ..config import Settings, load_profile
from ..models import Job
from ..store import Store
from . import actions


def run_browser(settings: Settings) -> None:
    """Entry point for the ``browse`` command."""
    try:
        from textual.app import App, ComposeResult
        from textual.containers import Vertical
        from textual.widgets import DataTable, Footer, Header, Static
        from textual import work
    except ImportError as exc:  # pragma: no cover - dependency guard
        raise RuntimeError(
            "Textual is required for the TUI (pip install -r requirements.txt)"
        ) from exc

    class JobHunterApp(App):
        CSS = "#detail { height: 40%; border: round $accent; padding: 1; }"
        BINDINGS = [
            ("f", "assess", "Assess fit"),
            ("d", "draft", "Draft"),
            ("b", "batch", "Batch on selected"),
            ("space", "toggle_select", "Select"),
            ("o", "show_detail", "Detail"),
            ("q", "quit", "Quit"),
        ]

        def __init__(self, settings: Settings) -> None:
            super().__init__()
            self._settings = settings
            self._store = Store(settings.db_path)
            self._profile = load_profile(settings)
            self._jobs: list[Job] = sorted(
                self._store.iter_filtered(), key=lambda j: j.keyword_score, reverse=True
            )
            self._selected: set[int] = set()
            self._ai_client: Optional[LLMClient] = None

        # ---- layout ----

        def compose(self) -> "ComposeResult":
            yield Header()
            with Vertical():
                yield DataTable(id="jobs")
                yield Static("Select a job and press 'f' (assess fit) or 'd' (draft).", id="detail")
            yield Footer()

        def on_mount(self) -> None:
            table = self.query_one("#jobs", DataTable)
            table.cursor_type = "row"
            table.add_columns("", "score", "title", "company", "location", "source", "fit", "draft")
            self._reload_rows()
            if not self._jobs:
                self._detail("No filtered jobs found. Run `aijobhunter run` first.")

        # ---- helpers ----

        def _ai(self) -> LLMClient:
            if self._ai_client is None:
                self._ai_client = build_llm_client(self._settings)
            return self._ai_client

        def _reload_rows(self) -> None:
            table = self.query_one("#jobs", DataTable)
            table.clear()
            for idx, job in enumerate(self._jobs):
                score = self._store.get_score(job.source, job.external_id)
                draft = self._store.get_draft(job.source, job.external_id)
                mark = "*" if idx in self._selected else ""
                table.add_row(
                    mark,
                    str(job.keyword_score),
                    (job.title or "?")[:40],
                    (job.company or "?")[:24],
                    (job.location or "")[:20],
                    job.source,
                    str(score.fit_score) if score else "",
                    "✓" if draft else "",
                    key=f"{job.source}:{job.external_id}",
                )

        def _cursor_job(self) -> Optional[Job]:
            table = self.query_one("#jobs", DataTable)
            row = table.cursor_row
            if 0 <= row < len(self._jobs):
                return self._jobs[row]
            return None

        def _targets(self) -> list[Job]:
            if self._selected:
                limit = self._settings.batch_size
                idxs = sorted(self._selected)[:limit]
                return [self._jobs[i] for i in idxs]
            job = self._cursor_job()
            return [job] if job else []

        def _detail(self, text: str) -> None:
            self.query_one("#detail", Static).update(text)

        # ---- actions ----

        def action_toggle_select(self) -> None:
            table = self.query_one("#jobs", DataTable)
            row = table.cursor_row
            if 0 <= row < len(self._jobs):
                self._selected.symmetric_difference_update({row})
                self._reload_rows()

        def action_show_detail(self) -> None:
            job = self._cursor_job()
            if not job:
                return
            score = self._store.get_score(job.source, job.external_id)
            draft = self._store.get_draft(job.source, job.external_id)
            parts = [
                f"[b]{job.title}[/b] — {job.company} ({job.location})",
                f"score {job.keyword_score} · matched: {', '.join(job.matched_keywords)}",
                f"link: {job.apply_link or job.url}",
            ]
            if score:
                parts.append(f"[b]Fit {score.fit_score}/100[/b]: {score.reason}")
            if draft:
                parts.append(f"Draft ({draft.channel.value}) → {draft.artifact_path or draft.target}")
            parts.append("")
            parts.append((job.description or "")[:2000])
            self._detail("\n".join(parts))

        def action_assess(self) -> None:
            self._run_action("assess", self._targets())

        def action_draft(self) -> None:
            self._run_action("draft", self._targets())

        def action_batch(self) -> None:
            if not self._selected:
                self.notify("Nothing selected — use space to select rows.")
                return
            self._run_action("assess", self._targets())

        def _run_action(self, kind: str, jobs: list[Job]) -> None:
            if not jobs:
                self.notify("No job under cursor.")
                return
            self.notify(f"{kind.title()} on {len(jobs)} job(s)… (LLM running)")
            self._worker(kind, jobs)

        @work(thread=True, exclusive=True)
        def _worker(self, kind: str, jobs: list[Job]) -> None:
            # Opens its own Store on THIS thread — sqlite3 connections cannot be
            # shared across threads, so we must not touch self._store here.
            ai = self._ai()
            errors = actions.run_actions(
                kind,
                self._settings.db_path,
                ai,
                jobs,
                self._profile,
                score_threshold=self._settings.score_threshold,
                output_dir=self._settings.output_dir,
            )
            for job, exc in errors:
                self.call_from_thread(self.notify, f"Error on {job.title}: {exc}")
            self.call_from_thread(self._reload_rows)
            self.call_from_thread(self.notify, f"{kind.title()} complete.")

        def on_unmount(self) -> None:
            self._store.close()

    JobHunterApp(settings).run()
