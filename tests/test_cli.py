from pathlib import Path

from scopequote import cli


def write_spec(tmp_path: Path, state: str = "draft") -> Path:
    path = tmp_path / "scopequote.toml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f"""
[quote]
title = "Example creative-service quote"
client = "Example Client"
project = "Example EP"
reference = "EXAMPLE-QUOTE-001"
currency = "EUR"
pricing_basis = "Fictional local quote declarations for review only."
amount_note = "Tax treatment, agreement, delivery, and payment must be confirmed separately."
state = "{state}"

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
""".strip(),
        encoding="utf-8",
    )
    return path


def write_amendment_spec(tmp_path: Path, state: str = "draft") -> Path:
    path = tmp_path / "scopequote-amendment.toml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f"""
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
""".strip(),
        encoding="utf-8",
    )
    return path


def test_check_returns_draft_review_code_and_scope_boundary(tmp_path: Path, capsys) -> None:
    code = cli.main(["check", str(write_spec(tmp_path))])

    captured = capsys.readouterr()
    assert code == 2
    assert "DECLARED QUOTE DRAFT" in captured.out
    assert "does not send the quote, create an invoice, or establish an agreement" in captured.out


def test_reviewed_check_and_draft_build_use_distinct_exit_codes(tmp_path: Path, capsys) -> None:
    draft_spec = write_spec(tmp_path)
    reviewed_spec = write_spec(tmp_path / "reviewed", state="reviewed")
    output = tmp_path / "quote"

    reviewed_code = cli.main(["check", str(reviewed_spec)])
    build_code = cli.main(["build", str(draft_spec), "--output", str(output)])
    rebuild_code = cli.main(["build", str(draft_spec), "--output", str(output)])

    captured = capsys.readouterr()
    assert reviewed_code == 0
    assert build_code == 2
    assert rebuild_code == 1
    assert (output / "QUOTE_DRAFT.md").is_file()
    assert "output directory already exists" in captured.err


def test_missing_quote_file_returns_input_error(tmp_path: Path, capsys) -> None:
    code = cli.main(["check", str(tmp_path / "missing.toml")])

    captured = capsys.readouterr()
    assert code == 1
    assert "No such file or directory" in captured.err


def test_amendment_check_and_build_keep_draft_state_local(tmp_path: Path, capsys) -> None:
    draft_spec = write_amendment_spec(tmp_path)
    reviewed_spec = write_amendment_spec(tmp_path / "reviewed", state="reviewed")
    output = tmp_path / "scope-change"

    check_code = cli.main(["amend", "check", str(draft_spec)])
    reviewed_code = cli.main(["amend", "check", str(reviewed_spec)])
    build_code = cli.main(["amend", "build", str(draft_spec), "--output", str(output)])
    rebuild_code = cli.main(["amend", "build", str(draft_spec), "--output", str(output)])

    captured = capsys.readouterr()
    assert check_code == 2
    assert reviewed_code == 0
    assert build_code == 2
    assert rebuild_code == 1
    assert "DECLARED SCOPE CHANGE DRAFT" in captured.out
    assert "Declared prior quote total: EUR 780.00" in captured.out
    assert "Proposed added-work total: EUR 430.00" in captured.out
    assert "Revised declared total: EUR 1210.00" in captured.out
    assert "does not verify a source quote" in captured.out
    assert (output / "SCOPE_CHANGE_DRAFT.html").is_file()
    assert "output directory already exists" in captured.err


def test_missing_amendment_file_returns_input_error(tmp_path: Path, capsys) -> None:
    code = cli.main(["amend", "check", str(tmp_path / "missing-amendment.toml")])

    captured = capsys.readouterr()
    assert code == 1
    assert "No such file or directory" in captured.err
