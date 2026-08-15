"""Declared additive scope-change calculations for local Scopequote review drafts."""

from __future__ import annotations

import csv
import hashlib
import io
import json
import tomllib
from dataclasses import dataclass
from html import escape
from pathlib import Path

from scopequote.config import (
    VALID_STATES,
    LineItem,
    nonnegative_integer,
    ordered_items,
    positive_integer,
    required_text,
    validate_unique_items,
)
from scopequote.service import CalculatedLine


@dataclass(frozen=True)
class Amendment:
    """Human-declared context for an additive local scope change, not an agreement."""

    title: str
    client: str
    project: str
    reference: str
    source_quote_reference: str
    currency: str
    prior_total_cents: int
    request_summary: str
    pricing_basis: str
    amount_note: str
    confirmation_note: str
    state: str


@dataclass(frozen=True)
class AmendmentSpec:
    """Validated declared scope-change inputs without verifying an earlier quote or approval."""

    amendment: Amendment
    items: tuple[LineItem, ...]


@dataclass(frozen=True)
class AmendmentAssessment:
    """Exact additive totals and human-declared state without commercial action assertions."""

    status: str
    lines: tuple[CalculatedLine, ...]
    prior_total_cents: int
    subtotal_cents: int
    discount_cents: int
    change_total_cents: int
    revised_total_cents: int


def amendment_currency(value: object) -> str:
    """Validate a display-only three-letter currency label without conversion."""

    code = required_text(value, "amendment.currency")
    if len(code) != 3 or not code.isascii() or not code.isalpha() or code != code.upper():
        raise ValueError("amendment.currency must be a three-letter uppercase code")
    return code


def load_spec(path: Path) -> AmendmentSpec:
    """Load a self-contained additive amendment without reading or changing a prior quote."""

    with path.open("rb") as stream:
        document = tomllib.load(stream)

    raw_amendment = document.get("amendment")
    if not isinstance(raw_amendment, dict):
        raise ValueError("[amendment] table is required")
    raw_items = document.get("change_items")
    if not isinstance(raw_items, list):
        raise ValueError("[[change_items]] entries are required")

    state = required_text(raw_amendment.get("state"), "amendment.state")
    if state not in VALID_STATES:
        raise ValueError("amendment.state must be draft or reviewed")
    amendment = Amendment(
        title=required_text(raw_amendment.get("title"), "amendment.title"),
        client=required_text(raw_amendment.get("client"), "amendment.client"),
        project=required_text(raw_amendment.get("project"), "amendment.project"),
        reference=required_text(raw_amendment.get("reference"), "amendment.reference"),
        source_quote_reference=required_text(
            raw_amendment.get("source_quote_reference"), "amendment.source_quote_reference"
        ),
        currency=amendment_currency(raw_amendment.get("currency")),
        prior_total_cents=nonnegative_integer(
            raw_amendment.get("prior_total_cents"), "amendment.prior_total_cents"
        ),
        request_summary=required_text(
            raw_amendment.get("request_summary"), "amendment.request_summary"
        ),
        pricing_basis=required_text(raw_amendment.get("pricing_basis"), "amendment.pricing_basis"),
        amount_note=required_text(raw_amendment.get("amount_note"), "amendment.amount_note"),
        confirmation_note=required_text(
            raw_amendment.get("confirmation_note"), "amendment.confirmation_note"
        ),
        state=state,
    )

    parsed_items: list[LineItem] = []
    for raw_item in raw_items:
        if not isinstance(raw_item, dict):
            raise ValueError("each [[change_items]] entry must be a TOML table")
        item = LineItem(
            position=positive_integer(raw_item.get("position"), "change item.position"),
            id=required_text(raw_item.get("id"), "change item.id"),
            service=required_text(raw_item.get("service"), "change item.service"),
            quantity=positive_integer(raw_item.get("quantity"), "change item.quantity"),
            unit=required_text(raw_item.get("unit"), "change item.unit"),
            unit_price_cents=nonnegative_integer(
                raw_item.get("unit_price_cents"), "change item.unit_price_cents"
            ),
            discount_cents=nonnegative_integer(
                raw_item.get("discount_cents"), "change item.discount_cents"
            ),
            included_revisions=nonnegative_integer(
                raw_item.get("included_revisions"), "change item.included_revisions"
            ),
            scope_note=required_text(raw_item.get("scope_note"), "change item.scope_note"),
        )
        if item.discount_cents > item.subtotal_cents:
            raise ValueError("change item discount_cents must not exceed line subtotal")
        parsed_items.append(item)

    items = tuple(parsed_items)
    validate_unique_items(items)
    return AmendmentSpec(amendment=amendment, items=ordered_items(items))


def assess(spec: AmendmentSpec) -> AmendmentAssessment:
    """Calculate exact declared additive totals without changing a prior quote."""

    lines = tuple(
        CalculatedLine(
            position=item.position,
            item_id=item.id,
            subtotal_cents=item.subtotal_cents,
            discount_cents=item.discount_cents,
            total_cents=item.total_cents,
        )
        for item in spec.items
    )
    subtotal_cents = sum(line.subtotal_cents for line in lines)
    discount_cents = sum(line.discount_cents for line in lines)
    change_total_cents = sum(line.total_cents for line in lines)
    prior_total_cents = spec.amendment.prior_total_cents
    return AmendmentAssessment(
        status=spec.amendment.state,
        lines=lines,
        prior_total_cents=prior_total_cents,
        subtotal_cents=subtotal_cents,
        discount_cents=discount_cents,
        change_total_cents=change_total_cents,
        revised_total_cents=prior_total_cents + change_total_cents,
    )


@dataclass(frozen=True)
class AmendmentBundle:
    """Files written by one non-overwriting local scope-change draft build."""

    output_path: Path
    files: tuple[Path, ...]
    manifest_path: Path


def format_cents(currency: str, amount_cents: int) -> str:
    """Format an exact nonnegative integer-cent amount without locale conversion."""

    return f"{currency} {amount_cents // 100}.{amount_cents % 100:02d}"


def markdown_cell(value: object) -> str:
    """Keep human declarations within one predictable Markdown table cell."""

    return str(value).replace("|", "\\|").replace("\r", " ").replace("\n", " ")


def html_text(value: object) -> str:
    """Render one declared value as text rather than browser-interpreted markup."""

    return escape(str(value), quote=True)


def scope_change_label(status: str) -> str:
    """Show the local human review state without asserting a client action."""

    if status == "draft":
        return "DECLARED SCOPE CHANGE DRAFT"
    return "DECLARED SCOPE CHANGE - HUMAN REVIEWED"


def calculated_line_by_id(assessment: AmendmentAssessment) -> dict[str, CalculatedLine]:
    """Index direct calculations by their validated IDs for deterministic rendering."""

    return {line.item_id: line for line in assessment.lines}


def render_markdown(spec: AmendmentSpec, assessment: AmendmentAssessment) -> str:
    """Render a local scope-change draft without obscuring its declared-only boundary."""

    calculations = calculated_line_by_id(assessment)
    lines = [
        f"# {spec.amendment.title}",
        "",
        f"**Status:** {scope_change_label(assessment.status)}  ",
        f"**Reference (declared):** {spec.amendment.reference}  ",
        f"**Source quote reference (declared):** {spec.amendment.source_quote_reference}  ",
        f"**Client (declared):** {spec.amendment.client}  ",
        f"**Project (declared):** {spec.amendment.project}",
        "",
        "## Declared additional work",
        "",
        (
            "| # | ID | Service | Quantity | Unit | Unit price | Discount | Line total | "
            "Included revisions | Scope note |"
        ),
        "| ---: | --- | --- | ---: | --- | ---: | ---: | ---: | ---: | --- |",
    ]
    for item in spec.items:
        calculation = calculations[item.id]
        lines.append(
            "| "
            + " | ".join(
                [
                    str(item.position),
                    markdown_cell(item.id),
                    markdown_cell(item.service),
                    str(item.quantity),
                    markdown_cell(item.unit),
                    format_cents(spec.amendment.currency, item.unit_price_cents),
                    format_cents(spec.amendment.currency, item.discount_cents),
                    format_cents(spec.amendment.currency, calculation.total_cents),
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
            (
                "- Declared prior quote total: "
                f"{format_cents(spec.amendment.currency, assessment.prior_total_cents)}"
            ),
            (
                "- Added-work subtotal: "
                f"{format_cents(spec.amendment.currency, assessment.subtotal_cents)}"
            ),
            (
                "- Explicit discounts: "
                f"{format_cents(spec.amendment.currency, assessment.discount_cents)}"
            ),
            (
                "- Proposed added-work total: "
                f"{format_cents(spec.amendment.currency, assessment.change_total_cents)}"
            ),
            (
                "- Revised declared total: "
                f"{format_cents(spec.amendment.currency, assessment.revised_total_cents)}"
            ),
            "",
            "## Declared request summary",
            "",
            spec.amendment.request_summary,
            "",
            "## Pricing basis",
            "",
            spec.amendment.pricing_basis,
            "",
            "## Amount note",
            "",
            spec.amendment.amount_note,
            "",
            "## Confirmation still required",
            "",
            spec.amendment.confirmation_note,
            "",
            "## Scope boundary",
            "",
            (
                "Scopequote calculates only the exact amounts declared in this local file. It does "
                "not verify a source quote, send this draft, or create an invoice. It does not "
                "establish an agreement, calculate tax, convert currency, record payment, reserve "
                "time, confirm scope, deliver work, or claim that a client reviewed, accepted, or "
                "paid anything."
            ),
            "",
        ]
    )
    return "\n".join(lines)


def render_client_summary(spec: AmendmentSpec, assessment: AmendmentAssessment) -> str:
    """Render concise, visibly unsent change-draft text for manual adaptation by a human."""

    lines = [
        "SCOPE CHANGE DRAFT - NOT SENT",
        f"Reference: {spec.amendment.reference}",
        f"Declared source quote reference: {spec.amendment.source_quote_reference}",
        f"For: {spec.amendment.client}",
        f"Project: {spec.amendment.project}",
        "",
        "Declared additional work:",
    ]
    for item in spec.items:
        calculation = next(line for line in assessment.lines if line.item_id == item.id)
        lines.append(
            f"- {item.quantity} {item.unit} x {item.service}: "
            f"{format_cents(spec.amendment.currency, calculation.total_cents)}"
        )
    lines.extend(
        [
            "",
            (
                "Declared prior quote total: "
                f"{format_cents(spec.amendment.currency, assessment.prior_total_cents)}"
            ),
            (
                "Proposed added-work total: "
                f"{format_cents(spec.amendment.currency, assessment.change_total_cents)}"
            ),
            (
                "Revised declared total: "
                f"{format_cents(spec.amendment.currency, assessment.revised_total_cents)}"
            ),
            "",
            "Confirmation still required:",
            spec.amendment.confirmation_note,
            "",
            (
                "This is a local human-declared scope-change draft. It has not been sent or "
                "accepted, and it is not an invoice, contract, payment record, tax calculation, "
                "booking confirmation, delivery confirmation, or proof that a client reviewed, "
                "accepted, or paid anything."
            ),
            "",
        ]
    )
    return "\n".join(lines)


def render_html(spec: AmendmentSpec, assessment: AmendmentAssessment) -> str:
    """Render a self-contained local scope-change review document for a browser."""

    calculations = calculated_line_by_id(assessment)
    rows = []
    for item in spec.items:
        calculation = calculations[item.id]
        unit_price = html_text(format_cents(spec.amendment.currency, item.unit_price_cents))
        discount = html_text(format_cents(spec.amendment.currency, item.discount_cents))
        line_total = html_text(format_cents(spec.amendment.currency, calculation.total_cents))
        rows.append(
            "\n".join(
                [
                    "      <tr>",
                    f'        <td class="numeric">{html_text(item.position)}</td>',
                    f"        <td>{html_text(item.id)}</td>",
                    f"        <td>{html_text(item.service)}</td>",
                    f'        <td class="numeric">{html_text(item.quantity)}</td>',
                    f"        <td>{html_text(item.unit)}</td>",
                    (f'        <td class="numeric">{unit_price}</td>'),
                    (f'        <td class="numeric">{discount}</td>'),
                    (f'        <td class="numeric">{line_total}</td>'),
                    f'        <td class="numeric">{html_text(item.included_revisions)}</td>',
                    f"        <td>{html_text(item.scope_note)}</td>",
                    "      </tr>",
                ]
            )
        )
    rendered_rows = "\n".join(rows)
    currency = spec.amendment.currency
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{html_text(spec.amendment.title)} - scope change draft</title>
  <style>
    :root {{
      color: #202124;
      background: #f4f2ed;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
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
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 1rem 2rem;
      margin-top: 2.5rem;
    }}

    .metadata div, .totals div {{
      border-top: 1px solid #d9d7d0;
      padding-top: 0.45rem;
    }}

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

    th, td {{
      padding: 0.65rem 0.45rem;
      border-bottom: 1px solid #d9d7d0;
      text-align: left;
    }}

    th {{
      color: #675b4b;
      font-size: 0.68rem;
      letter-spacing: 0.06em;
      text-transform: uppercase;
      vertical-align: bottom;
    }}

    .numeric {{ text-align: right; white-space: nowrap; }}

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
      <p class="eyebrow">Local client-review document</p>
      <h1>{html_text(spec.amendment.title)}</h1>
      <p class="status">SCOPE CHANGE DRAFT - NOT SENT</p>
      <dl class="metadata">
        <div>
          <dt>Declared state</dt>
          <dd>{html_text(scope_change_label(assessment.status))}</dd>
        </div>
        <div>
          <dt>Change reference</dt>
          <dd>{html_text(spec.amendment.reference)}</dd>
        </div>
        <div>
          <dt>Source quote reference</dt>
          <dd>{html_text(spec.amendment.source_quote_reference)}</dd>
        </div>
        <div>
          <dt>Client</dt>
          <dd>{html_text(spec.amendment.client)}</dd>
        </div>
        <div>
          <dt>Project</dt>
          <dd>{html_text(spec.amendment.project)}</dd>
        </div>
      </dl>
    </header>

    <section>
      <h2>Declared additional work</h2>
      <table>
        <thead>
          <tr>
            <th>#</th>
            <th>ID</th>
            <th>Service</th>
            <th class="numeric">Quantity</th>
            <th>Unit</th>
            <th class="numeric">Unit price</th>
            <th class="numeric">Discount</th>
            <th class="numeric">Line total</th>
            <th class="numeric">Included revisions</th>
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
      <dl class="totals">
        <div>
          <dt>Declared prior quote total</dt>
          <dd>{html_text(format_cents(currency, assessment.prior_total_cents))}</dd>
        </div>
        <div>
          <dt>Added-work subtotal</dt>
          <dd>{html_text(format_cents(currency, assessment.subtotal_cents))}</dd>
        </div>
        <div>
          <dt>Explicit discounts</dt>
          <dd>{html_text(format_cents(currency, assessment.discount_cents))}</dd>
        </div>
        <div>
          <dt>Proposed added-work total</dt>
          <dd>{html_text(format_cents(currency, assessment.change_total_cents))}</dd>
        </div>
        <div>
          <dt>Revised declared total</dt>
          <dd class="total">{html_text(format_cents(currency, assessment.revised_total_cents))}</dd>
        </div>
      </dl>
    </section>

    <section>
      <h2>Declared request summary</h2>
      <p class="prose">{html_text(spec.amendment.request_summary)}</p>
    </section>

    <section>
      <h2>Pricing basis</h2>
      <p class="prose">{html_text(spec.amendment.pricing_basis)}</p>
    </section>

    <section>
      <h2>Amount note</h2>
      <p class="prose">{html_text(spec.amendment.amount_note)}</p>
    </section>

    <section>
      <h2>Confirmation still required</h2>
      <p class="prose">{html_text(spec.amendment.confirmation_note)}</p>
    </section>

    <footer>
      This is a local human-declared scope-change draft. It has not been sent or accepted, and is
      not an invoice, contract, payment record, tax calculation, booking confirmation, delivery
      confirmation, or proof that a client reviewed, accepted, or paid anything.
    </footer>
  </main>
</body>
</html>
"""


def items_csv(spec: AmendmentSpec, assessment: AmendmentAssessment) -> str:
    """Return declared added-work data and direct exact-cent calculations in CSV format."""

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
    """Return a content hash for a generated local amendment-bundle artifact."""

    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_bundle(
    spec: AmendmentSpec, assessment: AmendmentAssessment, output_path: Path
) -> AmendmentBundle:
    """Write a fresh local amendment bundle while refusing to replace prior output."""

    if output_path.exists():
        raise FileExistsError(f"output directory already exists: {output_path}")
    output_path.mkdir(parents=True)

    markdown_path = output_path / "SCOPE_CHANGE_DRAFT.md"
    html_path = output_path / "SCOPE_CHANGE_DRAFT.html"
    csv_path = output_path / "scope-change-items.csv"
    summary_path = output_path / "client-summary.txt"
    markdown_path.write_text(render_markdown(spec, assessment), encoding="utf-8")
    html_path.write_text(render_html(spec, assessment), encoding="utf-8")
    csv_path.write_text(items_csv(spec, assessment), encoding="utf-8")
    summary_path.write_text(render_client_summary(spec, assessment), encoding="utf-8")
    files = (markdown_path, html_path, csv_path, summary_path)

    manifest_path = output_path / "manifest.json"
    manifest_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "kind": "scope_change_draft",
                "title": spec.amendment.title,
                "reference": spec.amendment.reference,
                "source_quote_reference": spec.amendment.source_quote_reference,
                "currency": spec.amendment.currency,
                "state": assessment.status,
                "prior_total_cents": assessment.prior_total_cents,
                "subtotal_cents": assessment.subtotal_cents,
                "discount_cents": assessment.discount_cents,
                "change_total_cents": assessment.change_total_cents,
                "revised_total_cents": assessment.revised_total_cents,
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
    return AmendmentBundle(output_path=output_path, files=files, manifest_path=manifest_path)
