"""Command-line interface for local Scopequote draft calculations."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from scopequote import config, report, service


def build_parser() -> argparse.ArgumentParser:
    """Create explicit local quote-review commands without client or financial integrations."""

    parser = argparse.ArgumentParser(
        prog="scopequote",
        description="Calculate a human-declared creative-service quote locally in exact cents.",
    )
    commands = parser.add_subparsers(dest="command", required=True)

    check = commands.add_parser(
        "check", help="Validate and calculate a quote without writing output."
    )
    check.add_argument("spec", type=Path, help="Path to a TOML quote declaration.")

    build = commands.add_parser("build", help="Write a new local quote-draft bundle.")
    build.add_argument("spec", type=Path, help="Path to a TOML quote declaration.")
    build.add_argument(
        "--output", required=True, type=Path, help="New output directory for the quote draft."
    )
    return parser


def print_assessment(spec: config.QuoteSpec, assessment: service.Assessment) -> None:
    """Print exact declared facts without implying an external client or financial action."""

    print(f"Quote: {spec.quote.title}")
    print(f"State: {report.quote_label(assessment.status)}")
    print(
        f"Declared quote total: {report.format_cents(spec.quote.currency, assessment.total_cents)}"
    )
    print(f"Proposed deposit: {report.format_cents(spec.quote.currency, assessment.deposit_cents)}")
    print(
        "Scopequote does not send the quote, create an invoice, or establish an agreement; "
        "calculate tax, record payment, reserve time, confirm scope, or deliver work."
    )


def main(argv: Sequence[str] | None = None) -> int:
    """Check a local declaration or write a separate quote-draft bundle for human use."""

    args = build_parser().parse_args(argv)
    try:
        spec = config.load_spec(args.spec)
        assessment = service.assess(spec)
        if args.command == "build":
            bundle = report.write_bundle(spec, assessment, args.output)
            print(f"Wrote local quote draft: {bundle.output_path}")
        print_assessment(spec, assessment)
    except (FileExistsError, FileNotFoundError, OSError, TypeError, ValueError) as error:
        print(f"scopequote: {error}", file=sys.stderr)
        return 1
    return 0 if assessment.status == "reviewed" else 2


if __name__ == "__main__":
    raise SystemExit(main())
