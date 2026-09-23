# 02 — Current State

_Assessment of `humalytix/feedback-intel` as of the 2026-09-22 checkout. Purpose: understand what exists before designing the visibility layer (stream rollups + master dashboard)._

---

## TL;DR

- **Five streams, two engines, overlapping populations.** The streams are lenses on the same Productboard notes, not partitions of them. Summing streams double-counts.
- **Only markdown is persisted.** The pipeline has per-note structured data (Productboard note ID, company, lifecycle, OCS, sentiment, intensity), but throws it away after rendering. Every aggregate we build today would have to re-parse prose.
- **There is no request taxonomy.** The model's per-note `category` is just `request / complaint / question / other`. Themes are deliberately uncountable (a design decision in Increment 7).
- **The time series has holes and overlaps.** There is a W29–W31 gap, and the W32 window for CE/Mobile/Pre-sales re-covers W27–W28.
- **The rollup layer is the repo's own #4 open item.** CE/Mobile monthly and quarterly rollups are unbuilt, and HANDOFF names them as the natural home for volume and trend. This project fits an existing gap rather than competing with anything.

---

## 1. Stream inventory

| Stream | Engine | Population | Weekly coverage | Rollups | Per-note table |
|---|---|---|---|---|---|
| `commercial-engine` | `judge` + `render` (Inc 3–7) | PB component `Billing` **or** classifier-judged pricing/licensing/billing | W25–W28, W32–W39 | none | Yes: Company · Who · Segment · Said · Sentiment·Intensity |
| `mobile` | `judge` + `render` | PB components `Mobile`, `Login / Sign Up` **or** classifier-judged | W25–W28, W32–W39 | none | Yes, same shape |
| `pre-sales` | `judge_presales` + `render_presales` | Gong calls where company resolves to `prospect` / `unknown` | W25–W28, W32–W39 | none | Yes: Contact · Wants · Blocker · Enthusiasm · Sentiment·Intensity |
| `ninetyio` | legacy `synthesize.py` | **All** notes in window (80–323/wk) | W26–W29, W32–W39 | Monthly Jul, Aug; quarterly empty | No. Prose with `[n]` refs grouped by 7 mission pods |
| `skunkworks` | legacy `synthesize.py` | **All** notes, read through an AI-native-bets lens | W26–W29, W32–W39 | Monthly Jul, Aug; quarterly empty | No. Prose "bet ledger" with `[n]` refs |

Weekly volume for the scoped streams is small: CE 6–31 notes/week, Mobile 5–19, Pre-sales 9–27 (excluding W32; see §5). `ninetyio` sees the full firehose of roughly 80–140 per normal week.

## 2. How the pipeline works (the parts that matter for us)

```
Productboard /v2/notes → scope (component / classifier / lifecycle)
    → enrich.py  (PB → HubSpot → Omni: company, lifecycle, OCS, archetype)
    → judge.py   (model returns ONLY: summary, category, sentiment, intensity, action)
    → render.py  (markdown)  → validate.py (fabrication gate)  → .md file → Confluence
```

The governing principle, from HANDOFF: **"code states facts, the model states judgment, nothing states both."** The model is never asked for a name, rank or count. Our layer should honor this, and it helps us. It argues that request counts and rankings must be computed by code from per-note labels, never written by a model into prose.

## 3. The biggest gap: no structured per-note output

`run_report.py` writes two things: the `.md` artifact and a tiny cursor file (`pipeline/state/<stream>_week.json`: last window end, label, count). The per-note records assembled in memory (note ID, facts, judgment, components, source) are discarded.

Consequences for the visibility layer:

- **No stable identity.** Rendered rows carry no Productboard note ID. `ninetyio`/`skunkworks` refs like `[34]` are indices within one week's digest, so `[34]` in W38 and `[34]` in W39 are unrelated notes.
- **No way to dedupe across streams.** See §4.
- **No request label to count on.** See §6.
- **Parsing markdown is lossy and brittle.** It's possible for the three table-based streams and impractical for the two prose streams.

**Implication:** the visibility layer needs its own per-note records. For the PoC, those come from parsing the table-based reports. Later, they come from Productboard directly. Everything downstream (rollups, ranking, trends, master view) reads those records, not the prose.

## 4. Streams overlap: the master view can't just sum them

Examples from W39 alone:

- **Bobo's Cafe / Craig Bernardi** appears in both Commercial Engine and Mobile (observer-role pricing touches billing *and* the login/seat surface).
- **Terry Dyck** and **Mukunth** appear in both Commercial Engine and Pre-sales.
- Every note in every scoped stream also appears in `ninetyio` and `skunkworks`, which cover the whole population.

The master dashboard must dedupe notes (on Productboard note ID once available; on company + contact + week in the PoC) and treat streams as **tags on a note**, not containers. A note can belong to several streams.

## 5. Time-series integrity

These affect any "trend over time" view:

| Issue | Where | Effect |
|---|---|---|
| **Gap W29–W31** | CE, Mobile, Pre-sales jump W28 → W32 | Missing weeks, unless W32 covers them (it does, below) |
| **W32 window = 2026-06-29 → 08-03** | CE, Mobile, Pre-sales | Five weeks in one report, overlapping W27 and W28. CE W32 shows 75 notes versus a typical ~20. Naively summing weeks **double-counts W27–W28**. |
| W29 = 2-day window, W32 = 19 days | `ninetyio`, `skunkworks` | No overlap, but uneven buckets. The Aug monthly already caveats this. |
| Windows are run timestamps, not midnight | W33 onward (delta cursor) | Report boundaries drift by hours. Minor, but "W39" ≠ ISO week 39 exactly. |

**Implication:** bucket by the note's own `createdAt` into ISO weeks, and dedupe on note ID. Never trust the report label as the time bucket.

## 6. Taxonomy: what exists and what doesn't

What we can build on:

- **Productboard components** are on ~87% of notes (per `productboard.py`). They give a coarse product area (Scorecard, Rocks, Billing, Mobile, Login…). This is a good **level-1 area**, but too coarse to be "the request."
- **`ninetyio`'s prose carry-forward** tracks "11 recurring themes" with promote/demote decisions and velocity arrows (⬆ ➡ ⬇). This is the closest thing to a request taxonomy today, but it lives in model prose, week to week, so it isn't countable or stable.
- **`ninetyio`'s "cross-source duplicates" section** already finds content-level dupes (`[82]≈[83]≈[84]`). That's evidence the clustering is feasible.
- **DESIGN.md already defines the target**: a *Theme* ("cluster of insights sharing a need") and a *Trend* ("theme measured over time: frequency, velocity, recency, source-mix").

What rules things out:

- **Productboard features can't be the anchor.** Note→feature links are mostly unprocessed (43/45 notes unlinked in W27), and DESIGN records a deliberate decision not to auto-link, since a wrong link pollutes the roadmap graph. Taxonomy is to be **emergent, held in our artifact layer**.
- **The judge's `category` field** (`request / complaint / question / other`) is a note *type*, not a *topic*. It's useful as a filter (requests vs. complaints), not as a ranking key.

### Note on Increment 7

Increment 7 chose not to make themes countable inside the weekly reports. That doesn't constrain us: the visibility layer lives outside Jon's pipeline and does its own labeling. It stays true to the repo's principle, since the model assigns each note a canonical request label (judgment, per note, auditable) and code does all counting, ranking and trending (facts).

## 7. The "Do" side (Omni)

Omni is live (`behavioral.py`). Currently available per report:

- **Aggregate OCS** across ~18.8k companies: at-risk %, mean, sub-scores for To-Dos, Rocks, Issues, Meetings/L10, Scorecard.
- **Per-note OCS / archetype** (Power User, Solid Operator, Struggler, Ghost, Newcomer) for 35–49% of notes. Gong-heavy weeks resolve fewer.
- **Lifecycle** (paying / trial / churned / prospect) via HubSpot, company-matched on 67–78% of notes.

`ninetyio` already runs a **say↔do** read per pod (e.g. "To-Dos corroborated: say↑ + do↓"). The master dashboard can surface this per request category, especially where a Productboard component maps cleanly to an OCS sub-score.

Known pending metrics (activation, trial-win, NRR, mobile-active) are marked `pending` in the reports and aren't available yet.

## 8. Source mix bias

Gong sales calls dominate intake: about 48–61% of `ninetyio` notes, and the large majority of CE rows. The pipeline itself warns that **call volume reflects the sales calendar, not demand**, and it weights unprompted in-app feedback higher in "To follow up." A volume-based ranking inherits this bias unless we adjust for it. That belongs in `04-ranking.md`.

## 9. The existing local browser (`scratch/build_site.py`)

- A zero-dependency Python script. It scans `<stream>/{weekly,monthly,quarterly}/*.md`, converts markdown to HTML with a purpose-built parser, and writes one static `scratch/index.html` (gitignored).
- It reads the `<!-- feedback-intel: audience=… period=… label=… window_from=… window_to=… -->` header for metadata.
- **The red dots mean "a churn-threatening note in this report."** The script flags any report whose text contains `churn-threatening` (an intensity value). They cluster in W25–W35 for Commercial Engine.
- It's a good shell to extend. The rollup and master views can be added as new sections fed by aggregated data rather than more markdown parsing.

## 10. Artifact hygiene issues found

These are worth fixing, or at least guarding against in any parser:

- **Duplicated metadata header** in 15 of the 28 `ninetyio`/`skunkworks` artifacts. In at least two, model chatter leaked above the report. `skunkworks/weekly/2026-W39.md` opens with the model talking about a scheduler call, and `ninetyio/monthly/2026-08.md` opens with a note about a tool. The CE/Mobile/Pre-sales engine doesn't have this problem.
- **`ninetyio`/`skunkworks` are still pre-Gong and on the legacy engine** (HANDOFF open item #5). They analyze the full population, but without the fabrication gates the newer engine has.
- **Pre-sales purity** is bounded by company resolution (~62–74%). Some former customers leak in as `prospect`, and the report discloses this.

---

## What this means for the build

1. **PoC source:** parse the three table-based streams into per-note records without touching the pipeline (see `03-data-model.md`).
2. **Full-population source (later):** pull notes directly from Productboard by date range, which adds real note IDs, true `createdAt` and the notes only Ninety.io sees today. The downstream schema stays the same.
3. **Taxonomy:** two levels. Level 1 is the Productboard component (code-owned). Level 2 is the canonical request (model-assigned per note, human-curated list, versioned in the repo).
4. **Aggregation:** bucket by note `createdAt` into ISO weeks, dedupe on note ID, and treat streams as tags.
5. **Views:** extend `build_site.py` with a stream rollup and a master view that read the aggregate, not the prose.
