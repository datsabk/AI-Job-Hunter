"""Command-line interface for AIJobHunter.

Workflow:
    python -m aijobhunter keywords     # 1+2: extract keywords from résumé, edit, add exclusions
    python -m aijobhunter run          # 3: collect → parse → keyword-filter → CSV (no LLM)
    python -m aijobhunter browse       # 4: TUI — assess fit / draft per job on demand
    python -m aijobhunter status       # show pipeline counts
    python -m aijobhunter export-csv   # re-export the CSV
"""

from __future__ import annotations

import argparse
import json
import logging
import sys

from .config import Settings, load_keywords, load_profile, save_keywords
from .pipeline import STAGE_ORDER, run_pipeline
from .store import Store


def _configure_logging(verbose: bool) -> None:
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
    )


def _parse_stages(value: str) -> list[str]:
    return [s.strip() for s in value.split(",") if s.strip()]


def _csv_list(value: str) -> list[str]:
    return [s.strip() for s in value.split(",") if s.strip()]


def build_parser() -> argparse.ArgumentParser:
    # Shared options usable before OR after the subcommand (e.g. `-v run` and
    # `run -v` both work). SUPPRESS avoids the subparser default overwriting a
    # value set on the top-level parser.
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument(
        "-v", "--verbose", action="store_true", default=argparse.SUPPRESS,
        help="debug logging",
    )

    parser = argparse.ArgumentParser(
        prog="aijobhunter", description="Multi-portal AI job hunter", parents=[common]
    )
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("keywords", parents=[common],
                   help="extract search keywords from your résumé (interactive)")

    run_cmd = sub.add_parser("run", parents=[common], help="collect → parse → keyword-filter → CSV")
    run_cmd.add_argument(
        "--stages",
        type=_parse_stages,
        default=STAGE_ORDER,
        help=f"comma-separated subset of {','.join(STAGE_ORDER)} (default: all)",
    )

    sub.add_parser("browse", parents=[common], help="open the TUI to assess/draft jobs on demand")
    sub.add_parser("status", parents=[common], help="show how many jobs sit at each pipeline status")

    csv_cmd = sub.add_parser("export-csv", parents=[common], help="export kept jobs to a CSV file")
    csv_cmd.add_argument(
        "path",
        nargs="?",
        default=None,
        help="output CSV path, or '-' for stdout (default: <output_dir>/jobs.csv)",
    )
    return parser


def _cmd_keywords(settings: Settings) -> int:
    """Interactive: LLM proposes keywords → user edits → adds exclusions → save."""
    from .ai.provider import build_llm_client
    from .stages.keywords import extract_keywords

    profile = load_profile(settings)
    print("Extracting keywords from your résumé via the local LLM…")
    proposed = extract_keywords(build_llm_client(settings), profile)

    if proposed:
        print("\nProposed include keywords:\n  " + ", ".join(proposed))
    else:
        print("\nThe model returned no keywords — enter your own below.")

    reply = input(
        "\nPress Enter to accept, or type a comma-separated list to replace: "
    ).strip()
    include = _csv_list(reply) if reply else proposed

    # Preserve any previously configured exclusions as the default hint.
    try:
        existing_exclude = load_keywords(settings)["exclude"]
    except Exception:  # noqa: BLE001
        existing_exclude = []
    hint = f" (current: {', '.join(existing_exclude)})" if existing_exclude else ""
    excl_reply = input(f"Enter EXCLUDE keywords, comma-separated{hint}: ").strip()
    exclude = _csv_list(excl_reply) if excl_reply else existing_exclude

    path = save_keywords(settings, include, exclude)
    print(f"\nSaved {len(include)} include and {len(exclude)} exclude keyword(s) to {path}")
    return 0


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    _configure_logging(getattr(args, "verbose", False))
    settings = Settings()

    if args.command == "keywords":
        return _cmd_keywords(settings)

    if args.command == "run":
        summary = run_pipeline(settings, args.stages)
        print(json.dumps(summary, indent=2, default=str))
        return 0

    if args.command == "browse":
        from .tui.app import run_browser

        run_browser(settings)
        return 0

    if args.command == "status":
        with Store(settings.db_path) as store:
            print(json.dumps(store.counts_by_status(), indent=2))
        return 0

    if args.command == "export-csv":
        from .stages.export_csv import run_export_csv

        with Store(settings.db_path) as store:
            count = run_export_csv(settings, store, args.path)
        if args.path != "-":
            print(f"Exported {count} job(s) to CSV.")
        return 0

    return 1


if __name__ == "__main__":
    sys.exit(main())
