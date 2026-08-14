import hashlib
import json
from pathlib import Path

import pytest

from scopequote import config, report, service


def example_spec() -> config.QuoteSpec:
    return config.QuoteSpec(
        quote=config.Quote(
            title="Example creative-service quote",
            client="Example Client",
            project="Example EP",
            reference="EXAMPLE-QUOTE-001",
            currency="EUR",
            pricing_basis="Fictional local quote declarations for review only.",
            amount_note=(
                "Tax treatment, agreement, delivery, and payment must be confirmed separately."
            ),
            state="draft",
        ),
        deposit=config.Deposit(
            amount_cents=30000,
            terms="Fictional proposed booking deposit for local review only.",
        ),
        items=(
            config.LineItem(
                position=1,
                id="mixing",
                service="Fictional stereo mix",
                quantity=2,
                unit="track",
                unit_price_cents=30000,
                discount_cents=0,
                included_revisions=2,
                scope_note="Fictional scope note.",
            ),
            config.LineItem(
                position=2,
                id="mastering",
                service="Fictional stereo master",
                quantity=2,
                unit="track",
                unit_price_cents=10000,
                discount_cents=2000,
                included_revisions=1,
                scope_note="Fictional scope note.",
            ),
        ),
    )


def test_renders_exact_totals_and_non_agreement_scope_boundary() -> None:
    rendered = report.render_markdown(example_spec(), service.assess(example_spec()))

    assert "# Example creative-service quote" in rendered
    assert "DECLARED QUOTE DRAFT" in rendered
    assert "EUR 780.00" in rendered
    assert "EUR 300.00" in rendered
    assert "EUR 480.00" in rendered
    assert "does not send the quote, create an invoice, or establish an agreement" in rendered


def test_writes_hashed_quote_bundle_without_overwriting(tmp_path: Path) -> None:
    output = tmp_path / "quote"
    bundle = report.write_bundle(example_spec(), service.assess(example_spec()), output)

    assert {path.name for path in bundle.files} == {
        "QUOTE_DRAFT.md",
        "client-summary.txt",
        "quote-items.csv",
    }
    assert "Fictional stereo master" in (output / "quote-items.csv").read_text(encoding="utf-8")
    assert "QUOTE DRAFT - NOT SENT" in (output / "client-summary.txt").read_text(encoding="utf-8")
    manifest = json.loads(bundle.manifest_path.read_text(encoding="utf-8"))
    assert manifest["total_cents"] == 78000
    assert (
        manifest["files"][0]["sha256"]
        == hashlib.sha256((output / "QUOTE_DRAFT.md").read_bytes()).hexdigest()
    )
    assert str(tmp_path) not in bundle.manifest_path.read_text(encoding="utf-8")

    with pytest.raises(FileExistsError, match="output directory already exists"):
        report.write_bundle(example_spec(), service.assess(example_spec()), output)
