from pathlib import Path

import pytest

from scopequote import config


def example_spec() -> str:
    return """
[quote]
title = "Example creative-service quote"
client = "Example Client"
project = "Example EP"
reference = "EXAMPLE-QUOTE-001"
currency = "EUR"
pricing_basis = "Fictional local quote declarations for review only."
amount_note = "Tax treatment, agreement, delivery, and payment must be confirmed separately."
state = "draft"

[deposit]
amount_cents = 30000
terms = "Fictional proposed booking deposit for local review only."

[[items]]
position = 1
id = "mixing"
service = "Fictional stereo mix"
quantity = 2
unit = "track"
unit_price_cents = 30000
discount_cents = 0
included_revisions = 2
scope_note = "Fictional scope note."

[[items]]
position = 2
id = "mastering"
service = "Fictional stereo master"
quantity = 2
unit = "track"
unit_price_cents = 10000
discount_cents = 2000
included_revisions = 1
scope_note = "Fictional scope note."
""".strip()


def write_spec(tmp_path: Path, content: str) -> Path:
    path = tmp_path / "scopequote.toml"
    path.write_text(content, encoding="utf-8")
    return path


def test_loads_exact_integer_cent_quote_declarations(tmp_path: Path) -> None:
    spec = config.load_spec(write_spec(tmp_path, example_spec()))

    assert spec.quote.currency == "EUR"
    assert spec.quote.state == "draft"
    assert spec.deposit.amount_cents == 30000
    assert [item.id for item in spec.items] == ["mixing", "mastering"]
    assert spec.items[1].discount_cents == 2000


def test_rejects_discount_larger_than_its_line_subtotal(tmp_path: Path) -> None:
    content = example_spec().replace("discount_cents = 2000", "discount_cents = 30000")

    with pytest.raises(ValueError, match="item discount_cents must not exceed line subtotal"):
        config.load_spec(write_spec(tmp_path, content))


def test_rejects_deposit_larger_than_declared_quote_total(tmp_path: Path) -> None:
    content = example_spec().replace("amount_cents = 30000", "amount_cents = 90000")

    with pytest.raises(ValueError, match="deposit amount_cents must not exceed quote total"):
        config.load_spec(write_spec(tmp_path, content))


def test_requires_contiguous_unique_item_positions_and_valid_currency(tmp_path: Path) -> None:
    duplicate = example_spec().replace('id = "mastering"', 'id = "MIXING"')
    gap = example_spec().replace("position = 2", "position = 3", 1)
    bad_currency = example_spec().replace('currency = "EUR"', 'currency = "EURO"')

    with pytest.raises(ValueError, match="item ids must be unique"):
        config.load_spec(write_spec(tmp_path, duplicate))
    with pytest.raises(ValueError, match="item positions must be contiguous"):
        config.load_spec(write_spec(tmp_path, gap))
    with pytest.raises(ValueError, match="quote.currency must be a three-letter uppercase code"):
        config.load_spec(write_spec(tmp_path, bad_currency))
