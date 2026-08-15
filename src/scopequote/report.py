"""Portable draft quote documents built from declared Scopequote arithmetic."""

from __future__ import annotations

import csv
import hashlib
import io
import json
from dataclasses import dataclass
from html import escape
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


def html_text(value: object) -> str:
    """Render one declared value as text rather than browser-interpreted markup."""

    return escape(str(value), quote=True)


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


def render_html(spec: QuoteSpec, assessment: Assessment) -> str:
    """Render a self-contained, unsent local quote-review document for a browser."""

    calculations = calculated_line_by_id(assessment)
    rows = []
    for item in spec.items:
        calculation = calculations[item.id]
        unit_price = html_text(format_cents(spec.quote.currency, item.unit_price_cents))
        discount = html_text(format_cents(spec.quote.currency, item.discount_cents))
        line_total = html_text(format_cents(spec.quote.currency, calculation.total_cents))
        rows.append(
            "\n".join(
                [
                    "      <tr>",
                    f'        <td class="numeric">{html_text(item.position)}</td>',
                    f"        <td>{html_text(item.service)}</td>",
                    f'        <td class="numeric">{html_text(item.quantity)}</td>',
                    f"        <td>{html_text(item.unit)}</td>",
                    f'        <td class="numeric">{unit_price}</td>',
                    f'        <td class="numeric">{discount}</td>',
                    f'        <td class="numeric">{line_total}</td>',
                    f'        <td class="numeric">{html_text(item.included_revisions)}</td>',
                    f"        <td>{html_text(item.scope_note)}</td>",
                    "      </tr>",
                ]
            )
        )
    rendered_rows = "\n".join(rows)
    currency = spec.quote.currency
    return f"""<!doctype html>
<html lang=\"en\">
<head>
  <meta charset=\"utf-8\">
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">
  <title>{html_text(spec.quote.title)} — quote draft</title>
  <style>
    :root {{
      color: #202124;
      background: #f4f2ed;
      font-family: -apple-system, BlinkMacSystemFont, \"Segoe UI\", sans-serif;
    }}

    * {{ box-sizing: border-box; }}

    body {{
      margin: 0;
      background: #f4f2ed;
      line-height: 1.45;
    }}

    main {{
      width: min(100% - 2rem, 68rem);
      margin: 2rem auto;
      padding: clamp(1.5rem, 4vw, 4rem);
      background: #ffffff;
      box-shadow: 0 0.8rem 3rem rgb(24 28 32 / 12%);
    }}

    h1, h2, p {{ margin: 0; }}

    h1 {{
      max-width: 32rem;
      font-size: clamp(2rem, 5vw, 4.25rem);
      line-height: 1;
      letter-spacing: -0.05em;
    }}

    h2 {{
      margin-bottom: 0.75rem;
      font-size: 0.9rem;
      letter-spacing: 0.08em;
      text-transform: uppercase;
    }}

    .eyebrow, .status {{
      font-size: 0.78rem;
      font-weight: 700;
      letter-spacing: 0.08em;
      text-transform: uppercase;
    }}

    .eyebrow {{ color: #675b4b; }}

    .status {{
      display: inline-block;
      margin-top: 1.5rem;
      padding: 0.4rem 0.55rem;
      color: #ffffff;
      background: #202124;
    }}

    .metadata, .totals {{
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 1rem 2rem;
      margin-top: 2.5rem;
    }}

    .metadata div, .totals div {{ border-top: 1px solid #d9d7d0; padding-top: 0.45rem; }}

    dt {{
      color: #675b4b;
      font-size: 0.7rem;
      font-weight: 700;
      letter-spacing: 0.08em;
      text-transform: uppercase;
    }}

    dd {{ margin: 0.15rem 0 0; font-weight: 600; }}

    section {{ margin-top: 3rem; }}

    table {{ width: 100%; border-collapse: collapse; font-size: 0.88rem; }}

    th, td {{ padding: 0.65rem 0.45rem; border-bottom: 1px solid #d9d7d0; text-align: left; }}

    th {{
      color: #675b4b;
      font-size: 0.68rem;
      letter-spacing: 0.06em;
      text-transform: uppercase;
      vertical-align: bottom;
    }}

    .numeric {{ text-align: right; white-space: nowrap; }}

    .totals {{ grid-template-columns: repeat(3, minmax(0, 1fr)); }}

    .total {{ color: #202124; font-size: 1.2rem; }}

    .prose {{ max-width: 48rem; white-space: pre-wrap; }}

    footer {{
      margin-top: 3rem;
      padding-top: 1rem;
      border-top: 1px solid #202124;
      font-size: 0.82rem;
    }}

    @media (max-width: 44rem) {{
      main {{ width: 100%; margin: 0; box-shadow: none; }}
      .metadata, .totals {{ grid-template-columns: 1fr; }}
      table {{ display: block; overflow-x: auto; }}
    }}

    @media print {{
      :root, body {{ background: #ffffff; }}
      main {{ width: auto; margin: 0; padding: 0; box-shadow: none; }}
      table {{ font-size: 8pt; }}
      th, td {{ padding: 0.3rem 0.2rem; }}
      section, tr {{ break-inside: avoid; }}
    }}
  </style>
</head>
<body>
  <main>
    <header>
      <p class=\"eyebrow\">Local client-review document</p>
      <h1>{html_text(spec.quote.title)}</h1>
      <p class=\"status\">QUOTE DRAFT — NOT SENT</p>
      <dl class=\"metadata\">
        <div>
          <dt>Declared state</dt>
          <dd>{html_text(quote_label(assessment.status))}</dd>
        </div>
        <div>
          <dt>Reference</dt>
          <dd>{html_text(spec.quote.reference)}</dd>
        </div>
        <div>
          <dt>Client</dt>
          <dd>{html_text(spec.quote.client)}</dd>
        </div>
        <div>
          <dt>Project</dt>
          <dd>{html_text(spec.quote.project)}</dd>
        </div>
      </dl>
    </header>

    <section>
      <h2>Declared scope and line items</h2>
      <table>
        <thead>
          <tr>
            <th>#</th>
            <th>Service</th>
            <th class=\"numeric\">Quantity</th>
            <th>Unit</th>
            <th class=\"numeric\">Unit price</th>
            <th class=\"numeric\">Discount</th>
            <th class=\"numeric\">Line total</th>
            <th class=\"numeric\">Included revisions</th>
            <th>Scope note</th>
          </tr>
        </thead>
        <tbody>
{rendered_rows}
        </tbody>
      </table>
    </section>

    <section>
      <h2>Exact declared totals</h2>
      <dl class=\"totals\">
        <div>
          <dt>Subtotal</dt>
          <dd>{html_text(format_cents(currency, assessment.subtotal_cents))}</dd>
        </div>
        <div>
          <dt>Explicit discounts</dt>
          <dd>{html_text(format_cents(currency, assessment.discount_cents))}</dd>
        </div>
        <div>
          <dt>Quote total</dt>
          <dd class=\"total\">{html_text(format_cents(currency, assessment.total_cents))}</dd>
        </div>
        <div>
          <dt>Proposed deposit</dt>
          <dd>{html_text(format_cents(currency, assessment.deposit_cents))}</dd>
        </div>
        <div>
          <dt>Balance after proposed deposit</dt>
          <dd>{html_text(format_cents(currency, assessment.balance_cents))}</dd>
        </div>
      </dl>
    </section>

    <section>
      <h2>Pricing basis</h2>
      <p class=\"prose\">{html_text(spec.quote.pricing_basis)}</p>
    </section>

    <section>
      <h2>Amount note</h2>
      <p class=\"prose\">{html_text(spec.quote.amount_note)}</p>
    </section>

    <section>
      <h2>Proposed deposit terms</h2>
      <p class=\"prose\">{html_text(spec.deposit.terms)}</p>
    </section>

    <footer>
      This is a local human-declared draft. It has not been sent or accepted, and is not an
      invoice, contract, payment record, tax calculation, booking confirmation, delivery
      confirmation, or proof that a client reviewed, accepted, or paid anything.
    </footer>
  </main>
</body>
</html>
"""


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
    html_path = output_path / "QUOTE_DRAFT.html"
    csv_path = output_path / "quote-items.csv"
    summary_path = output_path / "client-summary.txt"
    markdown_path.write_text(render_markdown(spec, assessment), encoding="utf-8")
    html_path.write_text(render_html(spec, assessment), encoding="utf-8")
    csv_path.write_text(quote_items_csv(spec, assessment), encoding="utf-8")
    summary_path.write_text(render_client_summary(spec, assessment), encoding="utf-8")
    files = (markdown_path, html_path, csv_path, summary_path)
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
