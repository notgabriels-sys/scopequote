import hashlib
import json
from dataclasses import replace
from html.parser import HTMLParser
from pathlib import Path

import pytest

from scopequote import amendment, config


class PassiveHtmlParser(HTMLParser):
    """Record active HTML elements and attributes that an offline brief must not contain."""

    forbidden_tags = {"a", "base", "embed", "form", "iframe", "img", "link", "object", "script"}
    forbidden_attributes = {"href", "onclick", "onerror", "src"}

    def __init__(self) -> None:
        super().__init__()
        self.active_tags: list[str] = []
        self.active_attributes: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in self.forbidden_tags:
            self.active_tags.append(tag)
        self.active_attributes.extend(
            name for name, _ in attrs if name in self.forbidden_attributes
        )


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


def test_renders_exact_additive_totals_and_local_only_boundary() -> None:
    rendered = amendment.render_markdown(example_spec(), amendment.assess(example_spec()))

    assert "# Example additional-work scope change" in rendered
    assert "DECLARED SCOPE CHANGE DRAFT" in rendered
    assert "Declared prior quote total: EUR 780.00" in rendered
    assert "Proposed added-work total: EUR 430.00" in rendered
    assert "Revised declared total: EUR 1210.00" in rendered
    assert "does not establish an agreement" in rendered


def test_html_escapes_declared_text_and_has_no_active_elements() -> None:
    spec = example_spec()
    hostile = replace(
        spec,
        amendment=replace(
            spec.amendment,
            title='<script>alert("title")</script>',
            client="Client & <review>",
            project="Project <draft>",
            reference="CHANGE & <001>",
            source_quote_reference="QUOTE & <001>",
            request_summary="Request & <review>",
            pricing_basis="Basis & <human review>",
            amount_note="Amount & <confirmation>",
            confirmation_note="Confirm & <response>",
        ),
        items=(
            replace(
                spec.items[0],
                id="change & <id>",
                service="Mix & <script>",
                unit="recall <unit>",
                scope_note="Scope & <review>",
            ),
            *spec.items[1:],
        ),
    )

    rendered = amendment.render_html(hostile, amendment.assess(hostile))
    parser = PassiveHtmlParser()
    parser.feed(rendered)

    assert "<!doctype html>" in rendered.lower()
    assert "SCOPE CHANGE DRAFT - NOT SENT" in rendered
    assert "EUR 1210.00" in rendered
    assert "not an invoice, contract, payment record" in " ".join(rendered.split())
    assert "&lt;script&gt;alert(&quot;title&quot;)&lt;/script&gt;" in rendered
    assert "Client &amp; &lt;review&gt;" in rendered
    assert "change &amp; &lt;id&gt;" in rendered
    assert "Confirm &amp; &lt;response&gt;" in rendered
    assert '<script>alert("title")</script>' not in rendered
    assert parser.active_tags == []
    assert parser.active_attributes == []


def test_writes_hashed_scope_change_bundle_without_overwriting(tmp_path: Path) -> None:
    output = tmp_path / "scope-change"
    bundle = amendment.write_bundle(example_spec(), amendment.assess(example_spec()), output)

    assert {path.name for path in bundle.files} == {
        "SCOPE_CHANGE_DRAFT.md",
        "SCOPE_CHANGE_DRAFT.html",
        "client-summary.txt",
        "scope-change-items.csv",
    }
    assert "Fictional additional stem preparation" in (output / "scope-change-items.csv").read_text(
        encoding="utf-8"
    )
    assert "SCOPE CHANGE DRAFT - NOT SENT" in (output / "client-summary.txt").read_text(
        encoding="utf-8"
    )
    html_draft = (output / "SCOPE_CHANGE_DRAFT.html").read_text(encoding="utf-8")
    assert "SCOPE CHANGE DRAFT - NOT SENT" in html_draft
    assert "not an invoice, contract, payment record" in " ".join(html_draft.split())

    manifest = json.loads(bundle.manifest_path.read_text(encoding="utf-8"))
    assert manifest["source_quote_reference"] == "EXAMPLE-QUOTE-001"
    assert manifest["prior_total_cents"] == 78000
    assert manifest["change_total_cents"] == 43000
    assert manifest["revised_total_cents"] == 121000
    manifest_files = {entry["path"]: entry for entry in manifest["files"]}
    assert set(manifest_files) == {path.name for path in bundle.files}
    for path in bundle.files:
        assert manifest_files[path.name]["sha256"] == hashlib.sha256(path.read_bytes()).hexdigest()
    assert str(tmp_path) not in bundle.manifest_path.read_text(encoding="utf-8")

    with pytest.raises(FileExistsError, match="output directory already exists"):
        amendment.write_bundle(example_spec(), amendment.assess(example_spec()), output)
