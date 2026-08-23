# Scopequote

Scopequote is a small offline CLI for calculating a **human-declared** creative-service
quote in exact integer cents. It is designed for the moment before a project is booked:
you list the proposed services, quantities, fixed-cent prices, explicit discounts, and a
proposed deposit; Scopequote checks the arithmetic and writes a readable local quote draft.

When extra work is proposed later, its separate `amend` command writes a new additive
scope-change draft rather than silently revising the original quote. It makes the declared
earlier reference, prior total, additional work, and revised declared total visible for local
human review.

It is not a rate card, invoice system, tax calculator, payment tool, contract, booking
system, email sender, or client portal. It never chooses a market rate, converts a
currency, adds tax, sends a quote, asks for payment, or claims that a client accepted
anything.

## Why this is separate from a work ledger

Use Scopequote **before** work is booked or billed, to make a proposed scope and amount
visible. Use a separate work ledger for declared work that has already been scheduled or
performed. A Scopequote `reviewed` state means only that a human reviewed this local
declaration; it does not establish a quote was sent, a booking was made, or a payment was
requested or received.

## What it checks and calculates

- required title, client, project, reference, currency, pricing basis, amount note, and
  proposed-deposit terms
- a display-only three-letter uppercase currency label, with no exchange-rate conversion
- ordered and case-insensitively unique quote item identifiers
- positive integral quantities; nonnegative integer-cent prices, discounts, and revisions
- each fixed-cent discount is no larger than its own line subtotal
- exact subtotal, explicit discount total, quote total, proposed deposit, and balance
- a proposed deposit that is not higher than the calculated quote total
- an explicit human-declared quote state: `draft` or `reviewed`
- for a separate amendment: a declared source-quote reference, declared prior total, additive
  line items, proposed added-work total, and revised declared total

All money arithmetic stays in integer cents. Scopequote rejects a declaration rather than
inventing a rounding method.

## What it does not prove

The generated documents do not prove an appropriate rate, tax treatment, scope agreement,
legal validity, client identity, sender/recipient, delivery timeline, work completion,
invoice, payment, booking, revision, or approval. Exact arithmetic is not financial,
accounting, legal, or tax advice.

## Install

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
```

## Use

Start from [examples/scopequote-example.toml](examples/scopequote-example.toml). Every
name, reference, scope, fee, discount, and deposit in it is fictional. It does not represent
an actual Hologram People, Lack of Fate, Fate Through, client, booking, project, agreement,
invoice, or payment.

```bash
scopequote check examples/scopequote-example.toml
scopequote build examples/scopequote-example.toml --output ./quote-draft
```

`check` writes nothing. `build` creates a new directory and refuses to replace an existing
path. It can create a draft bundle so the person preparing it can review it, but it remains
clearly labelled as unsent.

### Propose a declared scope change

If additional work is proposed after an initial quote, start from
[examples/scopequote-amendment-example.toml](examples/scopequote-amendment-example.toml). Its
references, project, services, and amounts are fictional. The declared source-quote reference
and prior total are not linked to, or verified against, an earlier Scopequote bundle.

```bash
scopequote amend check examples/scopequote-amendment-example.toml
scopequote amend build examples/scopequote-amendment-example.toml --output ./scope-change-draft
```

`amend` is additive-only: it makes newly proposed work and its exact declared change total
reviewable. It does not remove or credit work, revise an existing output folder, prove that an
earlier quote exists, send anything, or establish that anyone agreed to the change.

| Exit code | Meaning |
| --- | --- |
| `0` | The declaration is internally valid and a human marked it `reviewed`. It is not sent, accepted, booked, invoiced, or paid. |
| `2` | The declaration is internally valid but remains a local `draft`. |
| `1` | Invalid TOML, invalid arithmetic, inaccessible input, or an attempt to overwrite output. |

## Declaration shape

```toml
[quote]
title = "Example creative-service quote"
client = "Example Client"
project = "Example EP"
reference = "EXAMPLE-QUOTE-001"
currency = "EUR"
pricing_basis = "Written brief or clearly labelled local proposal."
amount_note = "Tax treatment, agreement, delivery, and payment must be confirmed separately."
state = "draft"

[deposit]
amount_cents = 30000
terms = "Proposed booking deposit; handle any actual request separately."

[[items]]
position = 1
id = "mixing"
service = "Declared stereo mix"
quantity = 2
unit = "track"
unit_price_cents = 30000
discount_cents = 0
included_revisions = 2
scope_note = "Human-declared scope note."
```

The currency field is a display label only. The amount note and deposit terms are text you
must write intentionally; Scopequote does not formulate or validate commercial, legal, tax,
or payment terms. Keep any rate or tax decision separate from the tool’s arithmetic.

## Initial-quote output bundle

`build` writes:

- `QUOTE_DRAFT.md` — readable declared scope, exact arithmetic, basis, terms, and boundary
- `QUOTE_DRAFT.html` — self-contained local browser-review view with the same declared scope,
  exact arithmetic, and visible `QUOTE DRAFT — NOT SENT` state
- `quote-items.csv` — all declared item fields plus calculated fixed-cent totals
- `client-summary.txt` — clearly marked `QUOTE DRAFT - NOT SENT` text for human adaptation
- `manifest.json` — SHA-256 hashes and byte counts for the four generated content files

Open `QUOTE_DRAFT.html` locally in a browser when a clean review or print layout is useful. Any
browser print/PDF action is initiated by you; Scopequote does not generate a PDF, send a quote,
or open a client-facing service.

The manifest records only the declared quote values and generated-artifact hashes; it does
not include the local input path, email, bank/payment data, invoice, contract, acceptance, or
transfer record.

## Scope-change output bundle

`scopequote amend build` writes a separate fresh directory containing:

- `SCOPE_CHANGE_DRAFT.md` — declared source reference, added work, exact totals, and boundary
- `SCOPE_CHANGE_DRAFT.html` — self-contained local browser-review view with a visible
  `SCOPE CHANGE DRAFT - NOT SENT` state
- `scope-change-items.csv` — all declared additional-work item fields plus calculated totals
- `client-summary.txt` — clearly marked unsent text for human adaptation
- `manifest.json` — declared references/totals plus SHA-256 hashes and byte counts for the four
  generated content files

The amendment manifest records only declared references/totals and generated-artifact hashes. It
does not contain a local input/output path, prove a source quote relationship, create an invoice,
record payment, prove confirmation, or evidence any external action. Open the HTML file locally
and use the browser's print command yourself if a print/PDF review is useful.

## Development

```bash
pytest -q
ruff check .
ruff format --check .
python -m compileall -q src
python -m build
```

Scopequote has no runtime dependencies beyond Python 3.11 or newer. Its tests use fictional
declarations only; they do not validate real pricing, tax treatment, agreements, invoices,
clients, bookings, payments, or work.

---

---

---

<!-- funnel-footer -->
Part of the Gabriel Tools + Code catalog — [browse all tools, products, repositories, and services](https://gabriel-tools-and-code.notgabriels960914.chatgpt.site/).

Free and open source: [theme-contrast](https://github.com/notgabriels-sys/theme-contrast) (WCAG contrast checking for colour themes) · [htmlshot](https://github.com/notgabriels-sys/htmlshot) (HTML → exact-size PNG/PDF) · [50 dark themes for Claude Code](https://github.com/notgabriels-sys/claude-code-50-dark-themes).

Hologram People soundware and Gabriel audio/product work are linked from the master catalog above.

Mixing and mastering enquiries — [public preview](https://gabriel-mixing-and-mastering-d1dmyt.v2.appdeploy.ai/).
