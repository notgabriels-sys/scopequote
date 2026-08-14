"""Portable draft quote documents built from declared Scopequote arithmetic."""

from __future__ import annotations

import csv
import hashlib
import io
import json
from dataclasses import dataclass
from pathlib import Path

from scopequote.config import QuoteSpec
from scopequote.service import Assessment, CalculatedLine


@dataclass(frozen=True)
class QuoteBundle:
    """Files written by one non-overwriting local quote-draft build."""

    output_path: Path
    files: tuple[Path, ...]
    manifest_path: Path


def format_cents(currency: str, amount_cents: int) -> str:
    """Format an exact nonnegative integer-cent amount without locale or conversion assumptions."""

    return f"{currency} {amount_cents // 100}.{amount_cents % 100:02d}"


def markdown_cell(value: object) -> str:
    """Keep user declarations within one predictable Markdown table cell."""

    return str(value).replace("|", "\\|").replace("\r", " ").replace("\n", " ")


def quote_label(status: str) -> str:
    """Make a local human review state visible without asserting client action or agreement."""

    return "DECLARED QUOTE DRAFT" if status == "draft" else "DECLARED QUOTE - HUMAN REVIEWED"


def calculated_line_by_id(assessment: Assessment) -> dict[str, CalculatedLine]:
    """Index direct calculations by their validated line IDs for deterministic rendering."""

    return {line.item_id: line for line in assessment.lines}


def render_markdown(spec: QuoteSpec, assessment: Assessment) -> str:
    """Render a quote draft without obscuring that all commercial context is human-declared."""

    calculations = calculated_line_by_id(assessment)
    lines = [
        f"# {spec.quote.title}",
        "",
        f"**Status:** {quote_label(assessment.status)}  ",
        f"**Reference (declared):** {spec.quote.reference}  ",
        f"**Client (declared):** {spec.quote.client}  ",
        f"**Project (declared):** {spec.quote.project}",
        "",
        "## Declared scope and line items",
        "",
        (
            "| # | Service | Quantity | Unit | Unit price | Discount | Line total | "
            "Included revisions | Scope note |"
        ),
        "| ---: | --- | ---: | --- | ---: | ---: | ---: | ---: | --- |",
    ]
    for item in spec.items:
        calculation = calculations[item.id]
        lines.append(
            "| "
            + " | ".join(
                [
                    str(item.position),
                    markdown_cell(item.service),
                    str(item.quantity),
                    markdown_cell(item.unit),
                    format_cents(spec.quote.currency, item.unit_price_cents),
                    format_cents(spec.quote.currency, item.discount_cents),
                    format_cents(spec.quote.currency, calculation.total_cents),
                    str(item.included_revisions),
                    markdown_cell(item.scope_note),
                ]
            )
            + " |"
        )
    lines.extend(
        [
            "",
            "## Exact declared totals",
            "",
            f"- Subtotal: {format_cents(spec.quote.currency, assessment.subtotal_cents)}",
            f"- Explicit discounts: {format_cents(spec.quote.currency, assessment.discount_cents)}",
            f"- Quote total: {format_cents(spec.quote.currency, assessment.total_cents)}",
            f"- Proposed deposit: {format_cents(spec.quote.currency, assessment.deposit_cents)}",
            (
                "- Balance after proposed deposit: "
                f"{format_cents(spec.quote.currency, assessment.balance_cents)}"
            ),
            "",
            "## Pricing basis",
            "",
            spec.quote.pricing_basis,
            "",
            "## Amount note",
            "",
            spec.quote.amount_note,
            "",
            "## Proposed deposit terms",
            "",
            spec.deposit.terms,
            "",
            "## Scope boundary",
            "",
            (
                "Scopequote calculates only the exact amounts declared in this local file. It does "
                "not send the quote, create an invoice, or establish an agreement; calculate tax, "
                "convert currency, record payment, reserve time, confirm scope, deliver work, or "
                "claim that a client reviewed, accepted, or paid anything."
            ),
            "",
        ]
    )
    return "\n".join(lines)


def render_client_summary(spec: QuoteSpec, assessment: Assessment) -> str:
    """Render concise, clearly unsent local quote text for manual adaptation by a human."""

    lines = [
        "QUOTE DRAFT - NOT SENT",
        f"Reference: {spec.quote.reference}",
        f"For: {spec.quote.client}",
        f"Project: {spec.quote.project}",
        "",
        "Declared items:",
    ]
    for item in spec.items:
        calculation = next(line for line in assessment.lines if line.item_id == item.id)
        lines.append(
            f"- {item.quantity} {item.unit} × {item.service}: "
            f"{format_cents(spec.quote.currency, calculation.total_cents)}"
        )
    lines.extend(
        [
            "",
            f"Declared quote total: {format_cents(spec.quote.currency, assessment.total_cents)}",
            f"Proposed deposit: {format_cents(spec.quote.currency, assessment.deposit_cents)}",
            (
                "Balance after proposed deposit: "
                f"{format_cents(spec.quote.currency, assessment.balance_cents)}"
            ),
            "",
            "This is a local human-declared draft. It has not been sent or accepted, and it is not "
            "an invoice, contract, payment record, tax calculation, booking confirmation, or "
            "delivery confirmation.",
            "",
        ]
    )
    return "\n".join(lines)


def quote_items_csv(spec: QuoteSpec, assessment: Assessment) -> str:
    """Return all declared scope and calculated exact-cent item data in a portable CSV table."""

    calculations = calculated_line_by_id(assessment)
    stream = io.StringIO(newline="")
    writer = csv.writer(stream, lineterminator="\n")
    writer.writerow(
        [
            "position",
            "item_id",
            "service",
            "quantity",
            "unit",
            "unit_price_cents",
            "subtotal_cents",
            "discount_cents",
            "line_total_cents",
            "included_revisions",
            "scope_note",
        ]
    )
    for item in spec.items:
        calculation = calculations[item.id]
        writer.writerow(
            [
                item.position,
                item.id,
                item.service,
                item.quantity,
                item.unit,
                item.unit_price_cents,
                calculation.subtotal_cents,
                item.discount_cents,
                calculation.total_cents,
                item.included_revisions,
                item.scope_note,
            ]
        )
    return stream.getvalue()


def sha256(path: Path) -> str:
    """Return a generated content hash for a portable review manifest."""

    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_bundle(spec: QuoteSpec, assessment: Assessment, output_path: Path) -> QuoteBundle:
    """Write a new local quote bundle while refusing to replace a prior output directory."""

    if output_path.exists():
        raise FileExistsError(f"output directory already exists: {output_path}")
    output_path.mkdir(parents=True)

    markdown_path = output_path / "QUOTE_DRAFT.md"
    csv_path = output_path / "quote-items.csv"
    summary_path = output_path / "client-summary.txt"
    markdown_path.write_text(render_markdown(spec, assessment), encoding="utf-8")
    csv_path.write_text(quote_items_csv(spec, assessment), encoding="utf-8")
    summary_path.write_text(render_client_summary(spec, assessment), encoding="utf-8")
    files = (markdown_path, csv_path, summary_path)
    manifest_path = output_path / "manifest.json"
    manifest_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "title": spec.quote.title,
                "reference": spec.quote.reference,
                "currency": spec.quote.currency,
                "state": assessment.status,
                "subtotal_cents": assessment.subtotal_cents,
                "discount_cents": assessment.discount_cents,
                "total_cents": assessment.total_cents,
                "deposit_cents": assessment.deposit_cents,
                "balance_cents": assessment.balance_cents,
                "files": [
                    {"path": path.name, "bytes": path.stat().st_size, "sha256": sha256(path)}
                    for path in files
                ],
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    return QuoteBundle(output_path=output_path, files=files, manifest_path=manifest_path)
