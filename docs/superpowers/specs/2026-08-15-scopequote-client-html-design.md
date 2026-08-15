# Scopequote client-review HTML draft — design

**Date:** 2026-08-15
**Status:** Approved through Gabriel's standing instruction to continue building useful GitHub tools autonomously.

## Problem

Scopequote already calculates a declared creative-service quote and produces a Markdown
draft, CSV, concise text summary, and integrity manifest. Markdown is useful for source
review, but a producer or engineer also needs a clean local view that can be opened in a
browser and reviewed or printed without copying quote information into a separate document.

## Decision

Add one generated, self-contained `QUOTE_DRAFT.html` artifact to the existing bundle.
The artifact is a static browser-review document, not a delivery mechanism or a new
commercial workflow. It is rendered from the same `QuoteSpec` and `Assessment` that already
drive the existing outputs, then listed with bytes and SHA-256 in `manifest.json`.

## User-facing behavior

`scopequote build INPUT.toml --output OUTPUT_DIR` will additionally write:

- `QUOTE_DRAFT.html` — an offline, printable review view of declared scope and exact totals.

The page will make its state visible in two ways:

- A prominent `QUOTE DRAFT — NOT SENT` label.
- A plain-language boundary: it is local human-declared material and is not an invoice,
  contract, payment record, tax calculation, booking confirmation, delivery confirmation,
  or proof of review, acceptance, or payment.

The user may invoke the browser's own print action if they want a paper/PDF representation.
Scopequote will not invoke a PDF engine, send email, create a payment link, open a portal,
or automate any external action.

## Rendering and safety

Data flow:

```text
QuoteSpec + Assessment
        |
        +--> render_html()
        |      |
        |      +--> QUOTE_DRAFT.html
        |
        +--> existing write_bundle() manifest file list + hashes
```

`render_html(spec, assessment)` will use only existing in-memory declared values and exact
cent calculations. Every declaration interpolated into HTML, including title, client,
project, reference, currency, pricing text, terms, service information, and scope notes,
will be escaped with Python's standard-library HTML escaping. Literal CSS and structural
markup are authored by Scopequote; there will be no JavaScript, remote font, image,
stylesheet, iframe, URL, local filesystem path, or network dependency.

The document is intentionally a semantic HTML table plus a small inline stylesheet. It uses
system fonts and `@media print` rules to improve local print review without changing quote
values or creating a file outside the caller-selected fresh output directory.

## Bundle and manifest behavior

The existing fresh-output guard remains the only write policy: if `OUTPUT_DIR` exists, the
build fails before producing another bundle. The HTML artifact will join the existing three
generated content files in `QuoteBundle.files`; the existing manifest then records its path
basename, byte count, and SHA-256 like every other generated content file. The manifest
continues not to include the local input path or external commercial data.

## Explicit non-goals

- No client portal, login, email, messaging, upload, analytics, or tracking.
- No invoice, contract, acceptance, signature, tax, currency conversion, payment, deposit
  collection, booking, delivery, or legal/commercial validation.
- No automatic PDF generation or browser control.
- No change to quote arithmetic, TOML schema, currencies, or state semantics.
- No use of actual client, price, artwork, audio, or contact data in tests or examples.

## Acceptance criteria

1. The normal build produces a fourth content artifact, `QUOTE_DRAFT.html`, and the manifest
   hashes it alongside the existing three files.
2. The HTML shows all declared items and exact existing totals, and clearly communicates its
   unsent, non-agreement boundary.
3. Hostile declaration text is rendered as text rather than executable/structural HTML.
4. The build remains local-only, dependency-free at runtime, and refuses an existing output
   directory exactly as before.
5. Existing behavior continues to pass tests, Ruff checks, formatting, compilation, package
   build, and an independent security-focused review.
