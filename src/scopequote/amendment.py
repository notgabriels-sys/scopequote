"""Declared additive scope-change calculations for local Scopequote review drafts."""

from __future__ import annotations

import tomllib
from dataclasses import dataclass
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
