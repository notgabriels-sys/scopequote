from pathlib import Path

import pytest

from scopequote import amendment, config


def example_toml(state: str = "draft") -> str:
    return f"""
[amendment]
title = "Example additional-work scope change"
client = "Example Client"
project = "Example EP"
reference = "EXAMPLE-CHANGE-001"
source_quote_reference = "EXAMPLE-QUOTE-001"
currency = "EUR"
prior_total_cents = 78000
request_summary = "Fictional additional recall work requested for local review only."
pricing_basis = "Fictional local declaration; rates and terms need separate confirmation."
amount_note = "Tax, delivery, agreement, and payment must be confirmed separately."
confirmation_note = "A separate human confirmation remains required."
state = "{state}"

[[change_items]]
position = 1
id = "additional-recall"
service = "Fictional additional mix recall"
quantity = 1
unit = "recall"
unit_price_cents = 15000
discount_cents = 0
included_revisions = 1
scope_note = "Fictional added-work scope note."

[[change_items]]
position = 2
id = "stem-delivery"
service = "Fictional additional stem preparation"
quantity = 2
unit = "track"
unit_price_cents = 15000
discount_cents = 2000
included_revisions = 0
scope_note = "Fictional added-work delivery note."
""".strip()


def write_spec(tmp_path: Path, content: str) -> Path:
    path = tmp_path / "scopequote-amendment.toml"
    path.write_text(content, encoding="utf-8")
    return path


def example_spec(state: str = "draft") -> amendment.AmendmentSpec:
    return amendment.AmendmentSpec(
        amendment=amendment.Amendment(
            title="Example additional-work scope change",
            client="Example Client",
            project="Example EP",
            reference="EXAMPLE-CHANGE-001",
            source_quote_reference="EXAMPLE-QUOTE-001",
            currency="EUR",
            prior_total_cents=78000,
            request_summary="Fictional additional recall work requested for local review only.",
            pricing_basis=(
                "Fictional local declaration; rates and terms need separate confirmation."
            ),
            amount_note="Tax, delivery, agreement, and payment must be confirmed separately.",
            confirmation_note=("A separate human confirmation remains required."),
            state=state,
        ),
        items=(
            config.LineItem(
                position=1,
                id="additional-recall",
                service="Fictional additional mix recall",
                quantity=1,
                unit="recall",
                unit_price_cents=15000,
                discount_cents=0,
                included_revisions=1,
                scope_note="Fictional added-work scope note.",
            ),
            config.LineItem(
                position=2,
                id="stem-delivery",
                service="Fictional additional stem preparation",
                quantity=2,
                unit="track",
                unit_price_cents=15000,
                discount_cents=2000,
                included_revisions=0,
                scope_note="Fictional added-work delivery note.",
            ),
        ),
    )


def test_loads_declared_additive_scope_change(tmp_path: Path) -> None:
    spec = amendment.load_spec(write_spec(tmp_path, example_toml()))

    assert spec.amendment.currency == "EUR"
    assert spec.amendment.prior_total_cents == 78000
    assert spec.amendment.state == "draft"
    assert [item.id for item in spec.items] == ["additional-recall", "stem-delivery"]
    assert spec.items[1].discount_cents == 2000


def test_assessment_keeps_prior_change_and_revised_totals_exact() -> None:
    assessment = amendment.assess(example_spec())

    assert assessment.status == "draft"
    assert assessment.prior_total_cents == 78000
    assert assessment.subtotal_cents == 45000
    assert assessment.discount_cents == 2000
    assert assessment.change_total_cents == 43000
    assert assessment.revised_total_cents == 121000
    assert assessment.lines[1].total_cents == 28000


def test_rejects_invalid_declared_scope_change_values(tmp_path: Path) -> None:
    empty_source_reference = example_toml().replace(
        'source_quote_reference = "EXAMPLE-QUOTE-001"', 'source_quote_reference = ""'
    )
    bad_currency = example_toml().replace('currency = "EUR"', 'currency = "EURO"')
    duplicate_id = example_toml().replace('id = "stem-delivery"', 'id = "ADDITIONAL-RECALL"')
    position_gap = example_toml().replace("position = 2", "position = 3", 1)
    excessive_discount = example_toml().replace("discount_cents = 2000", "discount_cents = 31000")
    source_reference_error = "amendment.source_quote_reference must be a nonempty string"
    currency_error = "amendment.currency must be a three-letter uppercase code"
    discount_error = "change item discount_cents must not exceed line subtotal"

    with pytest.raises(ValueError, match=source_reference_error):
        amendment.load_spec(write_spec(tmp_path, empty_source_reference))
    with pytest.raises(ValueError, match=currency_error):
        amendment.load_spec(write_spec(tmp_path, bad_currency))
    with pytest.raises(ValueError, match="item ids must be unique after case normalization"):
        amendment.load_spec(write_spec(tmp_path, duplicate_id))
    with pytest.raises(ValueError, match="item positions must be contiguous starting at 1"):
        amendment.load_spec(write_spec(tmp_path, position_gap))
    with pytest.raises(ValueError, match=discount_error):
        amendment.load_spec(write_spec(tmp_path, excessive_discount))
