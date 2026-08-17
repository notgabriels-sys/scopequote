"""Command-line interface for local Scopequote draft calculations."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from scopequote import amendment, config, report, service


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

    amend = commands.add_parser(
        "amend", help="Review a declared additive scope change locally without external actions."
    )
    amend_commands = amend.add_subparsers(dest="amend_command", required=True)
    amend_check = amend_commands.add_parser(
        "check", help="Validate and calculate a declared scope change without writing output."
    )
    amend_check.add_argument("spec", type=Path, help="Path to a TOML scope-change declaration.")
    amend_build = amend_commands.add_parser(
        "build", help="Write a new local scope-change draft bundle."
    )
    amend_build.add_argument("spec", type=Path, help="Path to a TOML scope-change declaration.")
    amend_build.add_argument(
        "--output",
        required=True,
        type=Path,
        help="New output directory for the scope-change draft.",
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


def print_amendment_assessment(
    spec: amendment.AmendmentSpec, assessment: amendment.AmendmentAssessment
) -> None:
    """Print local amendment facts without claiming a prior quote, client action, or agreement."""

    print(f"Scope change: {spec.amendment.title}")
    print(f"State: {amendment.scope_change_label(assessment.status)}")
    print(f"Declared source quote reference: {spec.amendment.source_quote_reference}")
    print(
        "Declared prior quote total: "
        f"{amendment.format_cents(spec.amendment.currency, assessment.prior_total_cents)}"
    )
    print(
        "Proposed added-work total: "
        f"{amendment.format_cents(spec.amendment.currency, assessment.change_total_cents)}"
    )
    print(
        "Revised declared total: "
        f"{amendment.format_cents(spec.amendment.currency, assessment.revised_total_cents)}"
    )
    print(
        "Scopequote does not verify a source quote, send this draft, create an invoice, or "
        "establish an agreement; calculate tax, record payment, reserve time, confirm scope, "
        "or deliver work."
    )


def main(argv: Sequence[str] | None = None) -> int:
    """Check a local declaration or write a separate quote-draft bundle for human use."""

    args = build_parser().parse_args(argv)
    try:
        if args.command == "amend":
            amendment_spec = amendment.load_spec(args.spec)
            amendment_assessment = amendment.assess(amendment_spec)
            if args.amend_command == "build":
                bundle = amendment.write_bundle(amendment_spec, amendment_assessment, args.output)
                print(f"Wrote local scope-change draft: {bundle.output_path}")
            print_amendment_assessment(amendment_spec, amendment_assessment)
            return 0 if amendment_assessment.status == "reviewed" else 2

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
