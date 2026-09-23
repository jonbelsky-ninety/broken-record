# VoC Dashboard — concept demo

A static, zero-backend concept demo of a customer-feedback visibility layer: a per-stream
weekly report browser with a cross-stream "master dashboard" (stack-ranked, weighted
friction score, week-over-week trend) mounted on top as the homepage.

**This is a sanitized mirror**, not the live tool. It exists to demo the concept and the UI
without exposing real customer data. See "About the data" below before treating anything in
here as real.

## View it

Open `index.html` directly in a browser — no server, no build step, no dependencies. Or serve
the folder with anything static (`python3 -m http.server`, Vercel, GitHub Pages, etc).

## Rebuild it

Only needed if you change `visibility/data/*.jsonl`, `visibility/taxonomy/*.yaml`, or a report
under `reports/`:

```bash
pip install -r requirements.txt
python3 visibility/scripts/aggregate.py   # notes + assignments + taxonomy -> aggregates.json
python3 build_site.py                     # -> index.html at the repo root
```

## Layout

```
index.html                  <- the built static site (what gets deployed)
assets/                      logo + icon
design_tokens.py             Terra (Ninety's design system) tokens, shared by both build scripts
build_site.py                 report browser + mounts the dashboard as its homepage
reports/<stream>/weekly/*.md  the per-week reports the browser renders
visibility/
  docs/            the design docs this was built from (the brief, data model, ranking math, build plan)
  taxonomy/        the canonical request taxonomy + ranking weights (requests.yaml, ranking.yaml)
  data/            notes.jsonl + assignments.jsonl (labeled data) -> aggregates.json (computed)
  scripts/         aggregate.py (pure scoring, no model calls) + build_site.py (the dashboard view)
```

## About the data

Every company name, contact name, and person mentioned anywhere in `reports/` and
`visibility/data/` has been replaced with a fictional placeholder. The underlying shape of
the feedback (what was asked, complaint severity, sentiment, which product area, which week)
is real and unmodified — only identities were swapped.

**How it was done:** every company/contact string was extracted from structured sources
(table columns, the `### Sources` list in each report, and the `notes.jsonl` fields), each
was mapped once to a fictional name, and every occurrence was replaced with regex-based
whole-word matching (so a short real name can't corrupt an unrelated word that merely
contains it) plus alias handling for company legal suffixes ("Inc.", "LLC", etc.) so the
same company matches with or without its suffix.

**What this does NOT guarantee:** a name mentioned only inside a quote or narrative aside —
never appearing in a Company/Contact field or Sources line — can't be found by this method.
A few such cases were found and hand-fixed during review; there's no way to prove none
remain in prose. For this reason, the two full-population legacy-engine streams
(`ninetyio`, `skunkworks` in the source project) are **deliberately excluded** from this
mirror — they're long free-form narrative reports with no structured extraction points, and
a spot-check found real names surviving multiple scrub passes. Only the three
table-structured, fully-verified streams (`commercial-engine`, `mobile`, `pre-sales`) are
included here.

If you add more source data to this mirror later, re-run the same kind of scrub before
publishing — don't assume new content is automatically covered.
