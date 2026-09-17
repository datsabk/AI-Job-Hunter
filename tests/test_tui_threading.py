"""Regression tests for cross-thread SQLite use in the TUI worker.

The TUI runs assess/draft in a background thread (Textual @work(thread=True)).
sqlite3 connections are confined to the thread that created them, so the worker
must open its OWN Store rather than reuse the main-thread one. These tests pin
that down.
"""

import sqlite3
import threading

from aijobhunter.models import Job, RawJob
from aijobhunter.store import Store
from aijobhunter.tui import actions


def _seed_job(db_path: str) -> Job:
    job = Job(source="src", external_id="1", url="http://x/1", title="Engineer")
    with Store(db_path) as s:
        s.add_raw(RawJob(source="src", external_id="1", url="http://x/1"))
        s.save_parsed(job)
    return job


def test_store_connection_is_thread_confined(tmp_path):
    """Documents the root cause: a Store used off its creating thread raises."""
    store = Store(str(tmp_path / "j.db"))
    captured: dict[str, BaseException] = {}

    def use_from_other_thread() -> None:
        try:
            store.exists("src", "1")
        except BaseException as exc:  # noqa: BLE001
            captured["err"] = exc

    t = threading.Thread(target=use_from_other_thread)
    t.start()
    t.join()
    store.close()
    assert isinstance(captured.get("err"), sqlite3.ProgrammingError)


def test_run_actions_draft_from_worker_thread(tmp_path):
    """The fix: run_actions opens its own Store, so it's safe off-thread."""
    db = str(tmp_path / "j.db")
    job = _seed_job(db)
    result: dict[str, list] = {}

    def worker() -> None:
        result["errors"] = actions.run_actions(
            "draft",
            db,
            ai=None,  # a linkless job hits the external-link fallback — no LLM call
            jobs=[job],
            profile={},
            score_threshold=70,
            output_dir=str(tmp_path / "out"),
        )

    t = threading.Thread(target=worker)
    t.start()
    t.join()

    assert result["errors"] == []
    # The main-thread connection sees the committed draft.
    with Store(db) as s:
        assert s.get_draft("src", "1") is not None
