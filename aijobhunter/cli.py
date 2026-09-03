"""Command-line interface for AIJobHunter.

Examples:
    python -m aijobhunter run                 # full pipeline: collect..export
    python -m aijobhunter run --stages collect,parse,score
    python -m aijobhunter status              # show pipeline counts
"""

from __future__ import annotations

import argparse
import json
import logging
import sys

from .config import Settings
from .pipeline import STAGE_ORDER, run_pipeline
from .store import Store


def _configure_logging(verbose: bool) -> None:
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
    )


def _parse_stages(value: str) -> list[str]:
    return [s.strip() for s in value.split(",") if s.strip()]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="aijobhunter", description="Multi-portal AI job hunter")
    parser.add_argument("-v", "--verbose", action="store_true", help="debug logging")
    sub = parser.add_subparsers(dest="command", required=True)

    run_cmd = sub.add_parser("run", help="run pipeline stages")
    run_cmd.add_argument(
        "--stages",
        type=_parse_stages,
        default=STAGE_ORDER,
        help=f"comma-separated subset of {','.join(STAGE_ORDER)} (default: all)",
    )

    sub.add_parser("status", help="show how many jobs sit at each pipeline status")

    csv_cmd = sub.add_parser("export-csv", help="export all listed jobs to a CSV file")
    csv_cmd.add_argument(
        "path",
        nargs="?",
        default=None,
        help="output CSV path, or '-' for stdout (default: <output_dir>/jobs.csv)",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    _configure_logging(args.verbose)
    settings = Settings()

    if args.command == "run":
        summary = run_pipeline(settings, args.stages)
        print(json.dumps(summary, indent=2, default=str))
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
