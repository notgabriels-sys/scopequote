# Scopequote scope-change amendment - design

**Date:** 2026-08-15  
**Status:** Approved through Gabriel's standing instruction to continue building useful GitHub tools autonomously.

## Problem

Scopequote makes an initial proposed creative-service scope and its arithmetic clear, but a
later request for additional work can still disappear into informal messages. That makes the
new scope, its exact add-on amount, and the human action still required easy to lose. This
feature should make a proposed scope change reviewable without mutating the original quote or
claiming a client accepted it.

## Approaches considered

1. Extend the original quote TOML with optional change fields. This would mix initial booking
   scope and later amendments in one output, making a previous version hard to preserve.
2. Read and compare an earlier generated quote bundle. This would imply a verified relationship
   to a prior quote and add filesystem coupling that the local tool cannot prove.
3. Create a separate, self-contained amendment declaration and bundle. This preserves the
   initial quote, keeps the claimed relationship explicitly human-declared, and gives the
   person preparing it one focused artifact to review. **This is the selected approach.**

## Decision

Add a separate `scopequote amend` command family. It reads an amendment TOML declaration,
checks exactly the declared additive line-item arithmetic, and optionally writes a fresh local
scope-change draft bundle. It will not change the existing `scopequote check` or
`scopequote build` commands, read a prior quote file, or claim that the declared source quote
exists, was sent, or was accepted.

## Declaration shape

The amendment TOML has one `[amendment]` table and one or more `[[change_items]]` tables.

```toml
[amendment]
title = "Example additional-work scope change"
client = "Example Client"
project = "Example EP"
reference = "EXAMPLE-CHANGE-001"
source_quote_reference = "EXAMPLE-QUOTE-001"
currency = "EUR"
prior_total_cents = 78000
request_summary = "Fictional additional recall work requested for local review only."
pricing_basis = "Fictional local declaration; rates and terms need separate human confirmation."
amount_note = "Tax, delivery, agreement, and payment remain separate from this local draft."
confirmation_note = "A separate human confirmation is still required before treating this as agreed."
state = "draft"

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
```

All string fields are required and trimmed. `currency` is an uppercase three-letter display
label only. `prior_total_cents`, prices, discounts, and revisions are integer values; no tax,
currency conversion, rate recommendation, or rounding method is introduced. Positions must be
contiguous from one, IDs must be case-insensitively unique, and an explicit discount cannot
exceed its own line subtotal. The declaration has the same human-only `draft` or `reviewed`
state vocabulary as an initial quote.

This first slice handles **additive** proposed work only. It does not model reductions, credits,
refunds, invoices, or payment adjustments. Zero-priced additions are allowed when a human needs
to make an included change visible, but their presence does not establish approval.

## Calculations and command behavior

`scopequote amend check INPUT.toml` reads no other file and writes nothing. It reports the
declared source-quote reference and prior total, the exact subtotal and explicit discounts for
the added line items, the exact proposed change total, and the revised declared total:
`prior_total_cents + change_total_cents`.

`scopequote amend build INPUT.toml --output OUTPUT_DIR` performs the same validation, creates a
new output directory, and refuses to overwrite any existing path. A valid `draft` returns exit
code `2`; a valid human-`reviewed` declaration returns `0`; malformed input, inaccessible input,
or a pre-existing output path returns `1`. `reviewed` remains a local human declaration, never a
client response or agreement.

## Output bundle

The new command writes a standalone local bundle:

- `SCOPE_CHANGE_DRAFT.md` - readable declared context, added work, exact totals, and boundary.
- `SCOPE_CHANGE_DRAFT.html` - static, self-contained browser and print review document.
- `scope-change-items.csv` - portable declared item fields plus calculated line totals.
- `client-summary.txt` - clearly marked `SCOPE CHANGE DRAFT - NOT SENT` text for manual adaptation.
- `manifest.json` - declared references/totals plus basenames, bytes, and SHA-256 hashes for the
  four content artifacts.

The manifest must not contain the local input path, output path, contact details, payment data,
or proof of any external event. It identifies `source_quote_reference` as a declaration rather
than a verified file or agreement relationship.

## Rendering and safety

Every declaration-derived value rendered into HTML, including title, client, project,
references, free-text notes, and all line-item fields, is escaped with Python's standard-library
HTML escaping before interpolation. The HTML contains literal structure and small inline CSS
only: no JavaScript, forms, remote URLs, fonts, images, iframes, browser control, analytics, or
network dependency. It visibly says `SCOPE CHANGE DRAFT - NOT SENT` and repeats that no
acceptance, agreement, invoice, booking, payment, delivery, or approval is established.

## Explicit non-goals

- No client portal, message, email, upload, signature, tracking, or payment flow.
- No invoice, contract, legal or tax advice, exchange conversion, payment or deposit calculation,
  scheduling, booking, delivery, or receipt.
- No automatic reading, verification, alteration, or linkage of an earlier quote bundle.
- No subtraction, credit, refund, or financial reconciliation workflow.
- No actual client, project, rate, audio, artwork, contact, payment, or agreement data in tests
  or examples.

## Acceptance criteria

1. `scopequote amend check` validates one self-contained TOML declaration and calculates exact
   prior, added, and revised integer-cent totals without modifying an initial quote workflow.
2. `scopequote amend build` creates exactly four content artifacts and a path-free manifest in a
   new local directory, while preserving existing-output refusal.
3. Every HTML declaration value is text-escaped; hostile data cannot create active markup or
   external resource references.
4. The CLI makes the distinction between a local draft and a local human-reviewed declaration
   explicit, and never represents either state as client acceptance.
5. Tests, linting, formatting, compilation, package build, installed-wheel smoke coverage, and a
   focused security diff review all pass before the change is published as a draft PR.
