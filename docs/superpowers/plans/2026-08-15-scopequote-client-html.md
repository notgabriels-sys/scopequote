# Scopequote client-review HTML draft — implementation plan

> **Implementation note:** Use this plan with the existing Scopequote branch
> `codex/scopequote-client-html`. The design is in
> `docs/superpowers/specs/2026-08-15-scopequote-client-html-design.md`.

## Goal

Add a safe, self-contained `QUOTE_DRAFT.html` to Scopequote's existing local quote-review
bundle without changing its quote arithmetic, TOML schema, or no-agreement boundary.

## Task 1: Establish renderer behavior with a failing test

**Files:**

- Modify: `tests/test_report.py`
- Modify: `src/scopequote/report.py`

1. Add a test that calls the planned `report.render_html(spec, assessment)` with the existing
   synthetic fixture.
2. Assert that it includes exact rendered totals, the `QUOTE DRAFT — NOT SENT` state label,
   the non-invoice/non-contract boundary, and representative declared scope.
3. Construct a separate synthetic `QuoteSpec` containing HTML-sensitive characters in quote
   metadata, service, scope note, and terms. Assert escaped text is present and raw structural
   markup such as `<script>` is absent.
4. Run the specific test and confirm it fails because `render_html` does not exist.
5. Implement `render_html` in `report.py` with only standard-library `html.escape`, literal
   structural markup/CSS, semantic tables, existing `format_cents`, and no script or external
   resource.
6. Rerun the focused renderer tests until they pass.

## Task 2: Add HTML to the evidence bundle with a failing test

**Files:**

- Modify: `tests/test_report.py`
- Modify: `src/scopequote/report.py`

1. Update the existing bundle test to expect `QUOTE_DRAFT.html` as the fourth generated
   content file and assert it includes the visible local-draft boundary.
2. Assert the manifest lists all four content files and that the HTML entry's SHA-256 matches
   the generated file.
3. Run the bundle test and confirm it fails before the writer is changed.
4. Add `html_path` in `write_bundle`, write `render_html(...)`, and include the path in the
   existing ordered `files` tuple before the manifest is written.
5. Rerun the focused bundle test. Confirm existing fresh-output rejection still passes.

## Task 3: Explain the intended human workflow

**Files:**

- Modify: `README.md`

1. Add `QUOTE_DRAFT.html` to the documented output bundle and correct the manifest count to
   four generated content files.
2. State that it is a local browser-review document; browser printing is manually initiated.
3. Restate the important boundary: Scopequote itself sends nothing and does not generate a
   PDF, invoice, contract, payment request, or external action.
4. Keep the existing no-path/no-commercial-record language accurate.

## Task 4: Verify the complete change and publish it safely

**Files:**

- Verify: all changed source, tests, docs, and package metadata as applicable

1. Run `pytest -q`, `ruff check .`, `ruff format --check .`, and `python -m compileall -q src`
   in an isolated environment.
2. Build an sdist/wheel and run a clean-environment smoke test using only the fictional
   example TOML. Inspect that the manifest reports four content artifacts and no absolute
   input path.
3. Run `git diff --check` and a security-focused scan emphasizing HTML escaping, absence of
   script/remote resources, manifest integrity, and non-overwriting local writes.
4. Commit each coherent change with clear messages.
5. Push the parent `codex/initial-implementation` branch first so its `.worktrees` ignore is
   available remotely, then push this child branch normally and create a **draft**, stacked PR
   against `codex/initial-implementation`. Do not merge, mark ready, or claim client/payment
   results.
