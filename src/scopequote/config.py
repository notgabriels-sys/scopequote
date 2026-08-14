"""TOML parsing for declared creative-service quote calculations."""

from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path

VALID_STATES = {"draft", "reviewed"}


@dataclass(frozen=True)
class Quote:
    """Human-declared context for a local quote draft, not an agreement or invoice."""

    title: str
    client: str
    project: str
    reference: str
    currency: str
    pricing_basis: str
    amount_note: str
    state: str


@dataclass(frozen=True)
class Deposit:
    """An explicit proposed deposit in exact cents without payment or receipt claims."""

    amount_cents: int
    terms: str


@dataclass(frozen=True)
class LineItem:
    """One ordered service line with exact declared price and scope descriptions."""

    position: int
    id: str
    service: str
    quantity: int
    unit: str
    unit_price_cents: int
    discount_cents: int
    included_revisions: int
    scope_note: str

    @property
    def subtotal_cents(self) -> int:
        """Calculate one declared line subtotal without any rounding rule."""

        return self.quantity * self.unit_price_cents

    @property
    def total_cents(self) -> int:
        """Return one declared line after its explicit fixed-cent discount."""

        return self.subtotal_cents - self.discount_cents


@dataclass(frozen=True)
class QuoteSpec:
    """Validated local quote inputs with no contact, tax, payment, or contract action."""

    quote: Quote
    deposit: Deposit
    items: tuple[LineItem, ...]


def required_text(value: object, field: str) -> str:
    """Return trimmed required text after rejecting unrelated TOML value types."""

    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be a nonempty string")
    return value.strip()


def positive_integer(value: object, field: str) -> int:
    """Require a positive integer while rejecting TOML booleans."""

    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ValueError(f"{field} must be a positive integer")
    return value


def nonnegative_integer(value: object, field: str) -> int:
    """Require a nonnegative integer-cent or count field without coercion."""

    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{field} must be a nonnegative integer")
    return value


def currency_code(value: object) -> str:
    """Validate a display-only ISO-style three-letter currency label without conversion."""

    code = required_text(value, "quote.currency")
    if len(code) != 3 or not code.isascii() or not code.isalpha() or code != code.upper():
        raise ValueError("quote.currency must be a three-letter uppercase code")
    return code


def required_table(document: dict[str, object], name: str) -> dict[str, object]:
    """Return one required TOML table with a stable validation message."""

    table = document.get(name)
    if not isinstance(table, dict):
        raise ValueError(f"[{name}] table is required")
    return table


def validate_unique_items(items: tuple[LineItem, ...]) -> None:
    """Reject IDs that would collide in a human or case-insensitive tool lookup."""

    ids = [item.id.casefold() for item in items]
    if len(ids) != len(set(ids)):
        raise ValueError("item ids must be unique after case normalization")


def ordered_items(items: tuple[LineItem, ...]) -> tuple[LineItem, ...]:
    """Require contiguous stable positions for quote and spreadsheet exports."""

    if not items:
        raise ValueError("at least one [[items]] entry is required")
    ordered = tuple(sorted(items, key=lambda item: item.position))
    positions = [item.position for item in ordered]
    if positions != list(range(1, len(ordered) + 1)):
        raise ValueError("item positions must be contiguous starting at 1")
    return ordered


def quote_total_cents(items: tuple[LineItem, ...]) -> int:
    """Calculate the exact sum of declared item totals without taxes or conversions."""

    return sum(item.total_cents for item in items)


def load_spec(path: Path) -> QuoteSpec:
    """Load a human-authored local quote without sending, invoicing, or accepting anything."""

    with path.open("rb") as stream:
        document = tomllib.load(stream)

    raw_quote = required_table(document, "quote")
    raw_deposit = required_table(document, "deposit")
    raw_items = document.get("items")
    if not isinstance(raw_items, list):
        raise ValueError("[[items]] entries are required")

    state = required_text(raw_quote.get("state"), "quote.state")
    if state not in VALID_STATES:
        raise ValueError("quote.state must be draft or reviewed")
    quote = Quote(
        title=required_text(raw_quote.get("title"), "quote.title"),
        client=required_text(raw_quote.get("client"), "quote.client"),
        project=required_text(raw_quote.get("project"), "quote.project"),
        reference=required_text(raw_quote.get("reference"), "quote.reference"),
        currency=currency_code(raw_quote.get("currency")),
        pricing_basis=required_text(raw_quote.get("pricing_basis"), "quote.pricing_basis"),
        amount_note=required_text(raw_quote.get("amount_note"), "quote.amount_note"),
        state=state,
    )
    deposit = Deposit(
        amount_cents=nonnegative_integer(raw_deposit.get("amount_cents"), "deposit.amount_cents"),
        terms=required_text(raw_deposit.get("terms"), "deposit.terms"),
    )

    parsed_items: list[LineItem] = []
    for raw_item in raw_items:
        if not isinstance(raw_item, dict):
            raise ValueError("each [[items]] entry must be a TOML table")
        item = LineItem(
            position=positive_integer(raw_item.get("position"), "item.position"),
            id=required_text(raw_item.get("id"), "item.id"),
            service=required_text(raw_item.get("service"), "item.service"),
            quantity=positive_integer(raw_item.get("quantity"), "item.quantity"),
            unit=required_text(raw_item.get("unit"), "item.unit"),
            unit_price_cents=nonnegative_integer(
                raw_item.get("unit_price_cents"), "item.unit_price_cents"
            ),
            discount_cents=nonnegative_integer(
                raw_item.get("discount_cents"), "item.discount_cents"
            ),
            included_revisions=nonnegative_integer(
                raw_item.get("included_revisions"), "item.included_revisions"
            ),
            scope_note=required_text(raw_item.get("scope_note"), "item.scope_note"),
        )
        if item.discount_cents > item.subtotal_cents:
            raise ValueError("item discount_cents must not exceed line subtotal")
        parsed_items.append(item)

    items = tuple(parsed_items)
    validate_unique_items(items)
    ordered = ordered_items(items)
    if deposit.amount_cents > quote_total_cents(ordered):
        raise ValueError("deposit amount_cents must not exceed quote total")
    return QuoteSpec(quote=quote, deposit=deposit, items=ordered)
