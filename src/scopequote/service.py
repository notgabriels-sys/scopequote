"""Exact-cent calculations for declared Scopequote line items."""

from __future__ import annotations

from dataclasses import dataclass

from scopequote.config import QuoteSpec


@dataclass(frozen=True)
class CalculatedLine:
    """One declared quote line with its directly derived fixed-cent amounts."""

    position: int
    item_id: str
    subtotal_cents: int
    discount_cents: int
    total_cents: int


@dataclass(frozen=True)
class Assessment:
    """Exact totals and declared review state without payment or agreement assertions."""

    status: str
    lines: tuple[CalculatedLine, ...]
    subtotal_cents: int
    discount_cents: int
    total_cents: int
    deposit_cents: int
    balance_cents: int


def assess(spec: QuoteSpec) -> Assessment:
    """Calculate declared line totals without selecting a rate, tax, or rounding method."""

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
    total_cents = sum(line.total_cents for line in lines)
    deposit_cents = spec.deposit.amount_cents
    return Assessment(
        status=spec.quote.state,
        lines=lines,
        subtotal_cents=subtotal_cents,
        discount_cents=discount_cents,
        total_cents=total_cents,
        deposit_cents=deposit_cents,
        balance_cents=total_cents - deposit_cents,
    )
