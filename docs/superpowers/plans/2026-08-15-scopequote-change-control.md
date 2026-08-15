# Scopequote scope-change amendment implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (- [ ]) syntax for tracking.

**Goal:** Add a separate offline Scopequote amendment command that turns a human-declared additive
scope change into exact, reviewable local draft artifacts.

**Architecture:** A new scopequote.amendment module owns the amendment TOML model, integer-cent
calculation, renderers, and fresh-output bundle writer. scopequote.cli dispatches the new nested
amend check and amend build commands while the existing initial-quote modules and commands stay
behaviorally unchanged. The amendment module reuses only the immutable LineItem model and basic
line-item ordering rules; it never reads or alters a prior quote bundle.

**Tech Stack:** Python 3.11+, standard-library tomllib, csv, hashlib, json, and html.escape;
pytest; Ruff; setuptools build backend.

## Global constraints

- All money values are declared integer cents; never choose a rate, tax treatment, currency
  conversion, rounding method, payment amount, or credit.
- An amendment is additive-only and self-contained; source_quote_reference and
  prior_total_cents are human declarations, not verified external facts.
- Runtime dependencies remain standard-library only; do not add a client portal, network call,
  PDF engine, browser automation, tracking, payment flow, or external service.
- Every declaration-derived HTML value must use html.escape(..., quote=True) before output.
- All output remains visibly local and unsent; reviewed is a human declaration, never client
  acceptance, agreement, payment, booking, delivery, or approval.
- Use fictional values only in tests and examples; existing scopequote check and scopequote build
  behavior must not regress.

---

### Task 1: Add a parsed amendment model and exact assessment

**Files:**

- Create: src/scopequote/amendment.py
- Create: tests/test_amendment.py

**Interfaces:**

- Consumes: scopequote.config.LineItem, VALID_STATES, ordered_items, and validate_unique_items.
- Produces: Amendment, AmendmentSpec, AmendmentAssessment, load_spec(path), and assess(spec) in
  scopequote.amendment.

- [ ] **Step 1: Write the failing model and calculation tests**

~~~python
from scopequote import amendment


def test_assessment_keeps_prior_change_and_revised_totals_exact() -> None:
    assessment = amendment.assess(example_spec())

    assert assessment.prior_total_cents == 78000
    assert assessment.change_total_cents == 43000
    assert assessment.revised_total_cents == 121000
~~~

Add parsing tests for a valid fictional TOML declaration plus an empty source reference, invalid
currency label, duplicate case-folded IDs, non-contiguous positions, and a discount above its line
subtotal. Name the assertions after the specific ValueError messages.

- [ ] **Step 2: Run the focused tests and verify they fail**

Run: uv run pytest tests/test_amendment.py -q  
Expected: collection failure because scopequote.amendment does not yet exist.

- [ ] **Step 3: Implement the minimal immutable model and parser**

~~~python
@dataclass(frozen=True)
class Amendment:
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
class AmendmentAssessment:
    status: str
    lines: tuple[CalculatedLine, ...]
    prior_total_cents: int
    subtotal_cents: int
    discount_cents: int
    change_total_cents: int
    revised_total_cents: int
~~~

Parse only [amendment] and [[change_items]]; require one or more items; validate the display-only
currency label and all exact integers; calculate the revised total by adding the nonnegative
declared prior total to the calculated additive change total.

- [ ] **Step 4: Run the focused tests and verify they pass**

Run: uv run pytest tests/test_amendment.py -q  
Expected: the model, parser, validation, and exact-cent assertions pass.

- [ ] **Step 5: Commit the model and its tests**

~~~bash
git add src/scopequote/amendment.py tests/test_amendment.py
git commit -m "feat: calculate declared scope amendments"
~~~

### Task 2: Render and hash a safe standalone amendment bundle

**Files:**

- Modify: src/scopequote/amendment.py
- Modify: tests/test_amendment.py

**Interfaces:**

- Consumes: AmendmentSpec and AmendmentAssessment from Task 1.
- Produces: render_markdown, render_html, render_client_summary, items_csv, write_bundle, and
  AmendmentBundle in scopequote.amendment.

- [ ] **Step 1: Write failing renderer, escaping, and bundle tests**

~~~python
def test_html_escapes_all_declared_values_and_has_no_active_elements() -> None:
    hostile = replace(
        example_spec(),
        amendment=replace(
            example_spec().amendment,
            title='<script>alert("title")</script>',
            confirmation_note='Text & <review>',
        ),
    )

    rendered = amendment.render_html(hostile, amendment.assess(hostile))

    assert '&lt;script&gt;alert(&quot;title&quot;)&lt;/script&gt;' in rendered
    assert '<script' not in rendered
    assert 'Text &amp; &lt;review&gt;' in rendered
~~~

Add an HTMLParser assertion that rejects script, img, iframe, object, embed, link, base, form, and
a elements plus src, href, onerror, and onclick attributes. Add a bundle test that expects exactly
SCOPE_CHANGE_DRAFT.md, SCOPE_CHANGE_DRAFT.html, scope-change-items.csv, and client-summary.txt,
verifies every manifest hash, and verifies the manifest omits the temporary output path.

- [ ] **Step 2: Run the focused tests and verify they fail**

Run: uv run pytest tests/test_amendment.py -q  
Expected: render_html and write_bundle are missing or the expected output files are absent.

- [ ] **Step 3: Implement static renderers and the fresh-output writer**

~~~python
def write_bundle(
    spec: AmendmentSpec, assessment: AmendmentAssessment, output_path: Path
) -> AmendmentBundle:
    if output_path.exists():
        raise FileExistsError(f"output directory already exists: {output_path}")
    output_path.mkdir(parents=True)
~~~

Render SCOPE CHANGE DRAFT - NOT SENT prominently in the HTML and client summary. Include the
declared source reference, prior total, added items, change total, revised declared total, request
summary, pricing basis, amount note, and confirmation note. Use semantic markup and small inline
CSS only; apply html.escape(..., quote=True) to every dynamic text value.

- [ ] **Step 4: Run the focused tests and verify they pass**

Run: uv run pytest tests/test_amendment.py -q  
Expected: rendered values, hostile-data safety, manifest evidence, and non-overwrite behavior pass.

- [ ] **Step 5: Commit the renderer and bundle behavior**

~~~bash
git add src/scopequote/amendment.py tests/test_amendment.py
git commit -m "feat: render scope-change review bundles"
~~~

### Task 3: Expose the command and document the deliberate boundary

**Files:**

- Modify: src/scopequote/cli.py
- Modify: tests/test_cli.py
- Create: examples/scopequote-amendment-example.toml
- Modify: README.md

**Interfaces:**

- Consumes: amendment.load_spec, amendment.assess, amendment.write_bundle, and the new example.
- Produces: scopequote amend check INPUT.toml and scopequote amend build INPUT.toml --output DIR.

- [ ] **Step 1: Write failing CLI tests**

~~~python
def test_amendment_check_and_build_keep_draft_state_local(tmp_path: Path, capsys) -> None:
    spec = write_amendment_spec(tmp_path, state="draft")
    output = tmp_path / "change"

    check_code = cli.main(["amend", "check", str(spec)])
    build_code = cli.main(["amend", "build", str(spec), "--output", str(output)])

    captured = capsys.readouterr()
    assert check_code == build_code == 2
    assert "SCOPE CHANGE DRAFT" in captured.out
    assert (output / "SCOPE_CHANGE_DRAFT.html").is_file()
~~~

Also test that reviewed returns 0, a missing amendment file returns 1, and a second build refuses
the existing output path with 1.

- [ ] **Step 2: Run the focused CLI tests and verify they fail**

Run: uv run pytest tests/test_cli.py -q  
Expected: argparse rejects the unimplemented amend command.

- [ ] **Step 3: Add nested amend subcommands and concise status output**

~~~python
amend = commands.add_parser("amend", help="Review a declared additive scope change locally.")
amend_commands = amend.add_subparsers(dest="amend_command", required=True)
~~~

Dispatch amendment commands through the new module and return 0 only for the human-declared
reviewed state. Keep every initial-quote command path and output untouched.

- [ ] **Step 4: Add the fictional example and README workflow**

Document the amendment declaration and exact commands; list its four output artifacts and manifest
boundary; state that the output is not sent, accepted, invoiced, paid, booked, or a verified
amendment to an earlier quote. Do not use actual pricing, client, project, or contact data.

- [ ] **Step 5: Run CLI and complete regression tests**

Run: uv run pytest tests/test_cli.py -q && uv run pytest -q  
Expected: amendment and original quote commands pass, with original quote behavior unchanged.

- [ ] **Step 6: Commit the command and documentation**

~~~bash
git add src/scopequote/cli.py tests/test_cli.py examples/scopequote-amendment-example.toml README.md
git commit -m "feat: add scopequote amendment commands"
~~~

### Task 4: Verify the packaged feature, security-review the diff, and publish a draft PR

**Files:**

- Verify: all changed source, tests, docs, and examples.

**Interfaces:**

- Consumes: the completed codex/scopequote-change-control branch.
- Produces: a pushed branch and a draft PR targeting codex/scopequote-client-html.

- [ ] **Step 1: Run complete local quality gates**

~~~bash
uv run pytest -q
uv run ruff check .
uv run ruff format --check .
python3 -m compileall -q src
git diff --check codex/scopequote-client-html..HEAD
~~~

Expected: every command succeeds with no warnings or whitespace errors.

- [ ] **Step 2: Test a freshly installed package with only fictional data**

Build the sdist and wheel, create a fresh temporary virtual environment, install the wheel, run
scopequote amend check and scopequote amend build against
examples/scopequote-amendment-example.toml, then independently check artifact names, manifest
hashes, and absence of the temporary source/output path.

- [ ] **Step 3: Complete a focused security diff scan**

Review the exact branch diff for TOML validation, integer arithmetic, safe output creation, HTML
escaping, absence of active/remote elements, manifest path leakage, and accidental external
actions. Record all changed files and findings; complete the scan before publishing.

- [ ] **Step 4: Publish the isolated branch as a draft stacked PR**

~~~bash
git push -u origin codex/scopequote-change-control
~~~

Create a **draft** PR from codex/scopequote-change-control into codex/scopequote-client-html;
summarize the capability, deliberate no-claim boundary, local checks, wheel smoke test, and security
review. Do not merge, mark ready, publish a package, or claim client acceptance, income, payment,
or adoption.

