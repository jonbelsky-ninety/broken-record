# 05 — Build Plan: the visibility layer inside the local browser

_How the data model (`03`) and taxonomy (`requests.yaml`) become views in the site you're building on top of `scratch/build_site.py`. Written to hand to Claude Code as the implementation brief._

---

## The shape

The site stays what it is today: **one static HTML file, no server, no dependencies**, rebuilt by a script. What changes is that the build gains a data pipeline in front of the renderer.

```
                      ┌──────────── build (Python, runs locally) ────────────┐
Productboard API ─┐   │                                                       │
   (token)        ├─► │ 1. source   → data/notes.jsonl        (cached)        │
report .md files ─┘   │ 2. label    → data/assignments.jsonl  (cached, model) │
                      │ 3. aggregate→ data/aggregates.json    (pure code)     │
requests.yaml ──────► │ 4. render   → index.html  (reports + rollups + master)│
                      └───────────────────────────────────────────────────────┘
                                              │
                          static page: aggregates embedded as JSON,
                          small inline JS for filters, sorting, charts
```

**One important nuance:** the page itself can't call Productboard or a model, because it's a static file opened from disk. All fetching and labeling happens in the **build step**, which is where the Productboard token and model access live. The page only renders what the build produced. That keeps secrets out of the HTML and makes the page instant to open and safe to share.

## Folder layout

Keep `build_site.py` as the entry point and split the new work into modules beside it, so the existing report browser keeps working throughout.

```
scratch/                      (or promote to visibility/ when it outgrows scratch)
  build_site.py               ← entry point; now calls the steps below, then renders
  fi_viz/
    sources/
      md.py                   ← parse CE / Mobile / Pre-sales report tables (works today)
      productboard.py         ← pull all notes by date range (needs token)
    label.py                  ← notes + requests.yaml → assignments (model call, cached)
    aggregate.py              ← notes + assignments → aggregates.json (no model)
    views/
      master.py               ← master dashboard HTML
      rollup.py               ← per-stream rollup HTML
      review.py               ← taxonomy review queue HTML
  taxonomy/requests.yaml
  taxonomy/ranking.yaml       ← score weights, min-evidence threshold, lens definitions
  data/                       ← generated; gitignore everything except overrides.yaml
    notes.jsonl
    assignments.jsonl
    overrides.yaml            ← your manual label corrections; survives relabels
    aggregates.json
```

Build command: `python scratch/build_site.py --source md` today, and `--source productboard --from 2026-06-15` once there's a token.

## Pipeline steps

### 1. Source (swappable)

Both adapters emit the same Note record from `03-data-model.md`. The rest of the pipeline doesn't know which one ran.

- **`md`** parses the three table streams, merges cross-stream duplicates on `company + contact + week`, drops the W32 rows that re-cover W27/W28, and joins the Sources list for `source`, `lifecycle` and `ocs`. This is what the seed files were built from.
- **`productboard`** fetches `/v2/notes` for the date range. It reuses the patterns in Jon's `pipeline/feedback_intel/productboard.py` (pagination, entity prefetch, component resolution) by importing or copying them. It adds real note IDs, true `createdAt` and the full population. Stream tags come from applying the same scope rules Jon uses (`domains.py`, `presales.py`), plus an `all` tag.

Notes are cached in `notes.jsonl` keyed by `note_id`, so rebuilds only fetch new ones.

### 2. Label (the only model step)

- Send batches of ~25 notes with the request definitions from `requests.yaml`. The model returns `{note_id: [{request_id, confidence}]}` with 0–3 labels each, and nothing else.
- Cache on `note_id + taxonomy_version`. A normal weekly rebuild labels only that week's new notes. Bumping the taxonomy version relabels everything.
- `overrides.yaml` wins over model output, always.
- **Model access:** Jon's pipeline uses the Claude Code CLI (`claude -p`) with a subscription token because Ninety's org blocks API-key self-serve (`synthesize.py`). Use the same approach, falling back to `ANTHROPIC_API_KEY` if one exists.
- Validate strictly: any `request_id` not in the YAML is dropped and logged, never rendered. This follows Jon's rule that the model can't invent facts.

### 3. Aggregate (pure code)

Compute the metrics table from `03` per `request × week × stream`: notes, companies, unprompted, paying, at-risk, intensity mix, weeks present, streams present, evidence IDs. Also compute per request:

- **Trend:** the last 4 weeks vs. the prior 4, normalized per week. The W29–W32 catch-up bucket is divided by its length.
- **Status tag:** `new` (first seen in last 2 weeks), `rising`, `steady`, `fading`.

Scoring follows `04-ranking.md`: the weighted company count (friction score) as the default sort, plus the Volume, Rising, At-risk and (M7) Revenue lenses. Weights live in `taxonomy/ranking.yaml`. Until M4 adds `source` and `lifecycle`, those weights default to 1.

### 4. Render

Embed `aggregates.json` in the page as a `<script type="application/json">` block, and render tables and charts with small inline JS. Charts are hand-rolled inline SVG (sparklines and small bar charts), which keeps the zero-dependency property. The current page is ~820 KB, and the aggregates add well under 1 MB.

---

## The views

### Sidebar

Add two new entry types above the weekly lists:

```
★ Master dashboard
COMMERCIAL ENGINE
  ▸ Rollup
  W39 …
MOBILE
  ▸ Rollup
  W39 …
…
⚙ Taxonomy review
```

### Master dashboard

The screen the cross-functional group debates from.

1. **Coverage banner.** It states exactly what population this is, e.g. "480 notes · Commercial Engine, Mobile, Pre-sales · W25–W39 · scoped streams only, core-workflow feedback under-represented." It disappears once the source is Productboard.
2. **Headline strip.** Four cards: top request by companies, biggest riser, newest request, count of at-risk accounts reporting friction.
3. **Stack-rank table.** One row per request, with columns for rank, request name, area, kind chip, friction score, companies, notes, weeks present, intensity mix, a 12-week sparkline, trend arrow, and stream chips (CE, MO, PS) showing where it surfaces. A lens switcher (Friction / Volume / Rising / At-risk) sits above it, and requests under 3 companies drop into an "Emerging" section below.
4. **Filters.** Kind, area, stream, lifecycle (paying / trial / prospect), date range, and "unprompted only." Every filter recomputes the ranking client-side from the embedded data.
5. **Evidence drawer.** Clicking a row opens the notes behind it: company, contact, lifecycle, week, summary, and a link to the weekly report where it appeared. This is what turns a debate about "is this real?" into one about priority.
6. **Area view toggle.** Collapse requests into their 17 areas for the 30-second read.

### Stream rollup

The same components scoped to one stream: stack-rank for that stream, volume per week, and top requests over time (a small multiples grid of the top 8 sparklines). Pre-sales can add a Blockers vs. Enthusiasm split, since its reports capture both.

### Taxonomy review

A working screen for you, not the room:

- Notes with **no label** or only **low-confidence** labels, grouped by similarity
- Requests with very few notes (merge candidates)
- Recent label changes after a taxonomy version bump

This is how the taxonomy stays healthy week to week.

---

## Build order

Each milestone produces something you can open and look at.

| # | Milestone | Done when |
|---|---|---|
| M1 | **Master view on seed data.** Load `notes.seed.jsonl` + `assignments.draft.jsonl` + `requests.yaml`, aggregate, render the stack-rank table and evidence drawer. | You can click any request and read its notes. |
| M2 | **Filters, sparklines, trend tags, coverage banner.** | Ranking changes correctly when filtering to one stream or kind. |
| M3 | **Stream rollups + sidebar entries.** | Each stream has a rollup page consistent with the master view filtered to that stream. |
| M4 | **`md` source adapter.** Replace the seed with a real extractor (adds Sources join: `source`, `lifecycle`, `ocs`). | Rebuilding after a new weekly report appears updates every view. |
| M5 | **Labeling automation + review screen.** | A new week's notes get labeled on build, and unlabeled notes show in review. |
| M6 | **`productboard` source.** Full population, real IDs and dates. | Coverage banner disappears; note count matches Ninety.io's weekly totals. |
| M7 | **Omni (Do side).** Company-level health joins and area↔sub-score overlays. | Each area shows its say↔do read. |

M1–M3 need no credentials and no model calls. They're pure UI work against the seed data, which is the fastest way to find out whether the views are what the room needs before investing in the pipeline behind them.

## Seed files

Built from this chat's analysis, so M1 can start immediately:

- **`notes.seed.jsonl`**: 480 deduplicated notes (company, contact, week, streams, sentiment, intensity, per-stream summaries, `empty` flag). No `source`, `lifecycle` or `ocs` yet; M4 adds those.
- **`assignments.draft.jsonl`**: 579 draft labels from the clustering read, covering 404 of the 451 notes with content. They're marked `assigned_by: draft-clustering`, good enough to build and judge the UI against, and replaced by the real labeling pass in M5.
- **`requests.yaml`**: taxonomy v0.1-draft.
