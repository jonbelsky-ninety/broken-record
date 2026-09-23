# 04 — Ranking

_How the master dashboard decides what's #1. The goal is a ranking a cross-functional room can argue **from**, not **about**: simple enough to explain in one sentence, and resistant to the obvious ways raw volume misleads._

---

## Why raw volume isn't enough

"Things we've heard over and over" is the right instinct. Counting notes directly has four known failure modes in this data:

1. **Chatty accounts.** One company on three calls in a week counts three times.
2. **The sales calendar.** Gong calls are ~50–90% of intake depending on stream. A heavy demo week inflates whatever prospects ask about, and the reports themselves warn about this.
3. **Severity blindness.** "Asked how observer seats work" and "charged after cancelling, demands refund" count the same.
4. **Spikes vs. persistence.** Five mentions in one week and one mention a week for five weeks look identical.

## Recommendation: a weighted company count

> **Friction score = the number of distinct companies raising it, where each company counts more if its feedback was severe, volunteered, or from an account we can't afford to lose, boosted slightly if it keeps recurring week after week.**

That's the one-sentence version for the room. The mechanics:

### Step 1: count companies, not notes

Each distinct company (or contact, when the company is unknown) contributes **once** per request, no matter how many notes it generated. This fixes failure mode 1.

### Step 2: weight each company

A company's weight = **intensity × source × account**, using its strongest note for that request.

| Factor | Values | Why |
|---|---|---|
| **Intensity** | mild 1 · strong 1.5 · churn-threatening 3 | Already captured on every note. Fixes severity blindness. |
| **Source** | convened (Gong/Intercom) 1 · volunteered (in-app) 1.5 | Mirrors the weighting Jon's reports already apply. Offsets the sales calendar. |
| **Account** | prospect/trial/unknown 1 · paying 1.25 · paying at-risk (Ghost/Struggler) 1.5 · churned 1.25 | Ties to the company mission of understanding churn. At-risk archetypes come from Omni via the report Sources lists. |

So a paying Struggler who volunteers a churn-threatening complaint weighs 3 × 1.5 × 1.5 = 6.75. A prospect asking a mild question on a sales call weighs 1. That's a big spread, but the distinct-company rule stops any single account from dominating.

### Step 3: boost for persistence

Multiply the request total by **1 + 0.5 × (weeks present ÷ weeks in range)**. Something heard every week gets up to a 50% boost, and a one-week spike gets almost none.

### What's deliberately *not* in the score

- **Trend.** Rising or fading is shown as its own column and sort, not mixed into the score. Mixing it in makes the ranking jumpy week to week, and the room loses trust in a list that reshuffles.
- **Kind.** Defects, gaps, confusion and pricing are ranked together by default, since friction is friction to a customer. The kind filter lets each function view its own slice.
- **Motivations and praise.** These are tracked separately and never compete with friction.

## Worked example on the seed data

Applying intensity and persistence (the seed files don't have source or account yet, which arrive with the `md` adapter in M4):

| Score rank | Volume rank | Request | Kind | Companies | Weeks (of 12) |
|---|---|---|---|---|---|
| 1 | 2 | Where do I start / core concepts | confusion | 28 | 11 |
| 2 | 1 | Who needs a paid seat | confusion | 28 | 11 |
| 3 | 3 | Price and ROI objections | pricing | 19 | 9 |
| 4 | 6 | Login and invite failures | defect | 17 | 9 |
| 5 | 4 | Fear the team won't adopt | adoption | 19 | 9 |
| 6 | 5 | Affordable implementation help | gap | 17 | 9 |
| 7 | 8 | Auto-populate scorecard from other systems | integration | 15 | 8 |
| 8 | 7 | Bulk import from Excel/CSV | gap | 15 | 8 |
| 9 | 11 | Cheaper seat for limited contributors | pricing | 13 | 10 |
| 10 | 9 | Other named tool integrations | integration | 15 | 6 |
| … | | | | | |
| **12** | **42** | **Cancellation and refund failures** | defect | 5 | 5 |

The top of the list barely moves, which is what you want: heavy volume stays heavy. The meaningful change is **cancellation failures jumping from #42 to #12**. Only five companies raised it, but they did so at high intensity across five separate weeks. Volume alone buried a billing defect with direct churn and trust consequences, and that's precisely the case the weighting exists to catch. Login failures moving up (#6 → #4) is the same effect at a smaller scale.

## Guardrails

- **Minimum evidence.** A request needs **3+ companies** to be ranked. Below that it's listed under "Emerging," so a single loud note can't take a top slot.
- **Show the ingredients.** The dashboard shows companies, notes, weeks present and intensity mix next to the score. Anyone who questions a rank can see why in one glance, and every number clicks through to the notes.
- **Coverage caveat.** Until the full population is in (M6), the banner reminds the room that core-workflow feedback is under-represented. No weighting fixes a missing population.
- **Weights live in config.** They go in `ranking.yaml` rather than code, so the group can tune them without a rebuild of logic. Changes to weights should be rare and announced; a ranking that changes because the formula changed looks like the data changed.

## Lenses (sort options on the dashboard)

| Lens | Sorts by | Question it answers |
|---|---|---|
| **Friction** (default) | Weighted score | What's causing the most meaningful pain right now? |
| **Volume** | Distinct companies | What are we hearing most often? |
| **Rising** | 4-week vs prior 4-week change | What's getting worse? |
| **At-risk** | Weighted score counting only paying at-risk accounts | What might be driving churn? |
| **Revenue** (M7, needs Omni/ARR) | Sum of ARR of companies raising it | How much money is attached? |

Different functions will reach for different lenses. Having them as named, fixed options keeps everyone arguing over the same numbers.

## Open for the group to decide

These are judgment calls rather than technical questions, and worth settling once, early:

1. **Churned accounts at 1.25?** Some teams weight churned feedback highest (they left, so it's the clearest signal). Others weight it lowest (can't win them back).
2. **Prospects vs. customers.** Should pre-sales blockers count equally with paying-customer friction, or should customers outweigh prospects across the board?
3. **Is intensity trustworthy enough to triple a company?** It's model judgment on each note (auditable but not code-guaranteed). If the room doubts it, cap churn-threatening at 2.
