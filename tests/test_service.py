from scopequote import config, service


def example_spec(state: str = "draft") -> config.QuoteSpec:
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
            state=state,
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


def test_calculates_exact_cent_totals_from_declared_line_items() -> None:
    assessment = service.assess(example_spec())

    assert assessment.status == "draft"
    assert assessment.subtotal_cents == 80000
    assert assessment.discount_cents == 2000
    assert assessment.total_cents == 78000
    assert assessment.deposit_cents == 30000
    assert assessment.balance_cents == 48000
    assert assessment.lines[1].total_cents == 18000


def test_reviewed_state_is_only_a_human_declaration_not_an_agreement() -> None:
    assessment = service.assess(example_spec(state="reviewed"))

    assert assessment.status == "reviewed"
    assert assessment.lines[0].item_id == "mixing"
