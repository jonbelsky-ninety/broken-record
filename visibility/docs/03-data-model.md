# 03 — Data Model

_How feedback becomes countable, rankable and trendable. Scope: the proof of concept, designed so later phases (full population, Omni) plug in without reworking what we build now._

---

## Design principles

1. **The note is the atom.** Every view is a count over notes. Nothing downstream reads report prose.
2. **Streams are tags, not containers.** One note can belong to several streams, and the master view counts it once.
3. **Code counts, the model labels.** This follows Jon's "code states facts, model states judgment" rule. The model assigns each note to a canonical request, and code does every count, rank and trend.
4. **Swappable source.** The note schema is the contract. In the PoC, notes come from parsing existing markdown. Later they come from a pipeline sidecar or a direct Productboard fetch. Everything downstream stays the same.
5. **Don't touch Jon's pipeline.** The PoC lives in its own folder and only *reads* the report files.

---

## PoC scope (no blockers)

Parsing the three table-based streams works today. I tested it against the checkout:

| Stream | Rows parsed |
|---|---|
| Commercial Engine | 260 |
| Pre-sales | 248 |
| Mobile | 150 |
| **Total** | **658** (534 unique contact-weeks after cross-stream merge) |

About **20% of contact-weeks appear in more than one stream**, which confirms that dedupe is necessary.

**The known limitation:** these three streams are *scoped* (pricing and billing, mobile and login, prospects). Most core-workflow feedback from existing customers (Scorecard, To-Dos, Rocks, data integrity) lives only in the Ninety.io stream, which is prose and not parseable per note. The PoC therefore proves the mechanics on a real but partial population. Phase 2 (below) closes the gap. This isn't a blocker to building; it's a caveat to state on the dashboard.

---

## Entities

```
Note  ──<  Assignment  >──  Request  >──  Area
  │                                         │
  └── company_id ─ ─ ─ (later) ─ ─ ─  AccountSnapshot (Omni)
                                            │
                          Area ─ ─ (later) ─ OCS sub-score
```

### 1. Note

One piece of feedback from one person. This is the only thing that gets counted.

| Field | Type | PoC source | Notes |
|---|---|---|---|
| `note_id` | string | hash of `company + contact + report week` | Becomes the Productboard note ID in Phase 2 |
| `week` | ISO week | report label | Becomes the note's `createdAt` in Phase 2 |
| `window_flag` | enum | derived | `normal` or `catch-up` (see W32 handling) |
| `streams` | list | which reports it appeared in | e.g. `["commercial-engine", "mobile"]` |
| `source` | enum | Sources list | `gong`, `intercom`, `in-app`, `manual` |
| `unprompted` | bool | derived from `source` | In-app = volunteered; Gong/Intercom = we convened it |
| `company` | string | table | `unknown` allowed |
| `contact` | string | table | |
| `lifecycle` | enum | Sources list | `paying`, `trial`, `churned`, `prospect`, `unknown` |
| `archetype` | enum | Segment column / Sources | Power User, Solid Operator, Struggler, Ghost, Newcomer |
| `ocs` | int or null | Sources list | Already Omni-derived, so this is a free Do-side signal in the PoC |
| `summary` | map | table | `{stream: text}`, since each stream summarized it independently |
| `wants` / `blocker` | string | pre-sales only | Richer than a summary; used for labeling |
| `sentiment` | enum | table | `positive`, `neutral`, `negative` |
| `intensity` | enum | table | `mild`, `strong`, `churn-threatening` |
| `provenance` | object | | `{extractor: "md-parse", files: [...], extracted_at}` |

Example, from a real W39 row:

```json
{
  "note_id": "n_7f3a91",
  "week": "2026-W39",
  "window_flag": "normal",
  "streams": ["commercial-engine"],
  "source": "intercom",
  "unprompted": false,
  "company": "Shift Collab",
  "contact": "Megan Rafuse",
  "lifecycle": "paying",
  "archetype": "Struggler",
  "ocs": 39,
  "summary": {"commercial-engine": "Wants a custom-meeting template library and a real 1:1 hub, and to trial a higher tier without losing Legacy; Maz can't build custom meetings."},
  "sentiment": "negative",
  "intensity": "strong",
  "provenance": {"extractor": "md-parse", "files": ["commercial-engine/weekly/2026-W39.md"]}
}
```

### 2. Request (the canonical taxonomy)

The thing we rank. It's a human-curated list, versioned in the repo as `taxonomy/requests.yaml`.

| Field | Notes |
|---|---|
| `id` | Stable slug, e.g. `excel-bulk-import` |
| `name` | Short, readable: "Bulk import from Excel" |
| `definition` | One sentence, plus what's **in** and what's **out**. This is what the labeling model reads. |
| `area` | Level-1 parent (see Area) |
| `kind` | `defect`, `gap`, `confusion`, `pricing`, `integration`, `praise` |
| `status` | `active`, `candidate`, `merged` |
| `merged_into` | When two requests turn out to be the same, history is kept |

**`kind` matters for your audience.** "Seat model confusion" and "Excel import is missing" are both friction, but one is a docs/UX/pricing-page fix and the other is a build. Filtering by kind lets CS, PMM and product each find their slice.

**The granularity test:** a request is specific enough that a team could scope it, and general enough that it recurs. "Import from Excel preserving original dates" is too narrow. "Data problems" is too broad. "Bulk import from Excel/CSV" is right. A practical check is whether two PMs reading two notes would agree they're asking for the same thing.

### 3. Area (level 1)

Fixed and short (about 15). It gives the master view a top-level roll-up and later becomes the join to Omni. Draft, aligned to Productboard components and OCS pillars:

Scorecard · Rocks · To-Dos · Issues · Meetings / L10 · Vision (VTO) · Accountability Chart · People / Reviews · Integrations & API · Auth & Access · Billing, Pricing & Seats · Mobile · Onboarding & Implementation · AI / Maz · Platform reliability & data integrity

### 4. Assignment

Links a note to 0–3 requests. It's kept separate from Note so that relabeling (after taxonomy changes) never touches the notes themselves.

| Field | Notes |
|---|---|
| `note_id`, `request_id` | |
| `confidence` | `high`, `medium`, `low`. Low-confidence assignments go to a review queue. |
| `assigned_by` | `model` or `human` (human overrides win) |
| `taxonomy_version` | Which `requests.yaml` version it was labeled against |

Multi-label is required. Shift Collab's single note contains three asks (templates, 1:1 hub, tier trial), and it counts once toward each.

### 5. Aggregate (computed, never hand-edited)

Generated per `request × week × stream`. This is what the site reads.

| Metric | Why it's there |
|---|---|
| `notes` | Raw volume (today's definition of "most requested") |
| `companies` | Unique companies, so one chatty account can't inflate a request |
| `unprompted` | Volunteered signal, which isn't driven by the sales calendar |
| `paying`, `at_risk` | At-risk = Ghost or Struggler archetype, or churn-threatening intensity |
| `intensity_mix` | Counts of mild / strong / churn-threatening |
| `sentiment_mix` | |
| `weeks_present` | Persistence versus a one-week spike (computed across the series) |
| `streams_present` | Breadth: whether it shows up in pre-sales, CE and mobile alike |
| `evidence` | List of `note_id`s, so every number in the dashboard clicks through to the actual quotes |

Scoring formulas belong in `04-ranking.md`. The model only needs to guarantee these inputs exist.

---

## Building the taxonomy (bootstrap)

The repo doesn't have a taxonomy, but it has good seeds:

- **Ninety.io's August monthly theme table:** To-Dos reliability, data integrity/persistence, access control, cross-team visibility, API completeness, onboarding disorientation, Scorecard demand, seat/licensing, enterprise identity (SSO/MFA).
- **Recurring themes in the scoped streams:** seat/observer confusion, Excel import, pricing sensitivity, integrations (Microsoft/Planner, Google Calendar, API push), data residency.
- **Productboard components**, for areas.

Process:

1. **Propose.** Run an LLM clustering pass over all 658 summaries (plus wants/blockers) and have it propose 30–50 requests with definitions, seeded with the themes above.
2. **Curate.** You edit the list: merge, split, rename, assign areas and kinds. This is the one step that must be human, and it's what makes the dashboard trustworthy to a cross-functional room.
3. **Freeze v1.** Commit `taxonomy/requests.yaml`.
4. **Label.** A model assigns each note to 0–3 requests with confidence, reading only the definitions.
5. **Review.** Check low-confidence and unassigned notes. Recurring unassigned asks become `candidate` requests, and they get promoted once they reach a threshold (e.g. 3+ companies).
6. **Ongoing.** New weeks get labeled against the current version. Taxonomy changes trigger a relabel, which is cheap because Assignment is separate from Note.

---

## Handling the data problems from `02-current-state.md`

**Cross-stream duplicates.** Merge on `company + contact + week`. The merged note gets both streams as tags and keeps both summaries.

**W32 catch-up window (06-29 → 08-03).** Of the W27/W28 contacts, 23/25 (CE), 21/21 (Mobile) and 22/23 (Pre-sales) reappear in W32, which confirms the overlap. The rule:

- Drop W32 rows whose contact already appears in W27 or W28 of the same stream.
- Keep the rest and bucket them as **W29–W32** with `window_flag: catch-up`.
- Trend charts show that bucket per-week-normalized and visibly marked, rather than as a false spike.

**Report windows ≠ ISO weeks.** This is accepted for the PoC, and it's fixed in Phase 2 when notes carry a real `createdAt`.

---

## Folder structure

Everything lives in one new top-level folder, next to Jon's work rather than inside it:

```
visibility/
  docs/                      ← these briefs (01-brief, 02-current-state, 03-data-model, …)
  taxonomy/
    requests.yaml            ← curated, versioned; the only hand-edited data file
    areas.yaml
  data/
    notes.jsonl              ← generated by extract
    assignments.jsonl        ← generated by label (+ human overrides)
    overrides.yaml           ← manual corrections that survive relabels
    aggregates.json          ← generated by aggregate; what the site reads
  scripts/
    extract_md.py            ← reports → notes.jsonl   (Phase 2: swap for extract_pb.py)
    propose_taxonomy.py      ← one-time clustering pass
    label.py                 ← notes + taxonomy → assignments
    aggregate.py             ← notes + assignments → aggregates.json
    build_site.py            ← extends the existing browser with rollup + master views
```

The pipeline is four commands: `extract → label → aggregate → build`. Only `label` calls a model.

---

## Phasing

**Phase 1 (PoC).** Three table streams, markdown-parsed, curated taxonomy, stream rollups and master view. Needs nothing from Jon and no API credentials beyond a model for labeling.

**Phase 2 (full population).** Swap `extract_md.py` for `extract_pb.py`, which pulls notes directly from Productboard by date range. This adds real note IDs, true `createdAt`, the 80–140 notes a week that only Ninety.io sees today, and component links. It needs a Productboard API token (the pipeline's `.env` already uses one). Nothing downstream changes.

**Phase 3 (Omni, the "Do" side).** It slots in through two join keys that already exist in this model:

- **`company_id` on Note → AccountSnapshot** (OCS, sub-scores, archetype, lifecycle, and ARR if available over time). This enables revenue-weighted ranking and "is this request concentrated in at-risk accounts?"
- **`area` on Request → OCS sub-score.** Scorecard maps to the Scorecard sub-score, To-Dos to To-Dos, and so on. This gives each area a say↔do read: *loud and behavior is weak* (real friction) versus *loud but behavior is strong* (feature demand from healthy users). Jon's Ninety.io reports already make this distinction in prose; the dashboard would make it a chart.

We don't need Omni for the PoC. Per-note OCS and archetype already come through the report Sources lists, so there's some Do-side signal from day one.
