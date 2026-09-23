# 01 — Brief: Feedback Visibility Layer

_One page. What we're building, for whom, and how we'll know it worked._

---

## The problem

Ninety already collects and summarizes customer feedback well. Jon Utter's feedback-intel pipeline turns Productboard notes (Gong calls, Intercom, in-app) into weekly reports for five streams: Commercial Engine, Mobile, Pre-sales, Ninety.io and Skunkworks. Those reports are good at answering *"what happened this week?"*

They can't answer the questions a cross-functional team needs to prioritize:

- What are customers asking for **most**, across every stream?
- How do those asks **rank** against each other?
- Which are **growing**, which are fading, and which have been there all along?

Today, answering those means reading dozens of weekly reports and tallying by memory. The result is that prioritization debates run on anecdote, and each function arrives with its own version of the truth.

## What we're building

A visibility layer on top of the existing reports, delivered as views in a local browser site:

1. **Stream rollups.** For each stream, the top requests over time rather than week by week.
2. **Master dashboard.** Every stream combined and deduplicated, with requests stack-ranked and trended, and every number clickable through to the customer notes behind it.

Under the hood, each piece of feedback is labeled against a shared, curated list of canonical requests (`requests.yaml`), so "Excel import" in one week and "bulk upload issues from a spreadsheet" in another count as the same thing.

## Who it's for

**Primary:** the cross-functional group that prioritizes friction work, meaning Product, Design, CS and PMM. They need aligned visibility into the biggest friction points so they can debate priority and commit to action plans against them.

What each function gets:

| Function | Uses it to… |
|---|---|
| Product & Design | See which gaps and defects are most widespread and persistent; size problems before scoping |
| CS | Spot recurring confusion and at-risk-account pain; find content and enablement gaps |
| PMM | Understand pricing and packaging friction, objections, and why prospects buy |

**Secondary:** leadership, for a quick read on what customers are struggling with.

## Goals

1. **One shared ranked list** of friction points that every function trusts, because every number is traceable to real notes.
2. **Trends over time**: what's new, rising, steady or fading.
3. **Low upkeep**: rebuilding weekly takes one command; labeling new feedback is automated.
4. **Built on what exists**: reuse Jon's pipeline outputs and principles rather than duplicating them.

## Non-goals (for now)

- **Changing Jon's pipeline.** The visibility layer only reads its outputs.
- **Writing back to Productboard.** No automated note→feature linking.
- **Deciding priorities.** The dashboard informs the debate; the group makes the call.
- **A hosted app.** It stays a static page for the PoC. Hosting can come later if it earns it.

## How we'll know it worked

- The cross-functional group **uses the master dashboard** in its prioritization discussions instead of ad hoc summaries.
- Debates shift from *"is this real?"* to *"what do we do about it?"*, because the evidence is one click away.
- At least one prioritization decision in the first month **cites the dashboard's ranking or trend**.
- The weekly rebuild takes **minutes**, not a manual read-through.

## Phasing

| Phase | Scope | Needs |
|---|---|---|
| **PoC (M1–M5)** | Commercial Engine, Mobile and Pre-sales, parsed from existing reports (~480 notes). Master view, rollups, automated labeling. | Nothing beyond model access for labeling |
| **Full population (M6)** | Every Productboard note (~1,600 over the same weeks), real IDs and dates | A Productboard API token |
| **Say + Do (M7)** | Account health and usage from Omni alongside feedback, e.g. "loud complaints *and* weak usage" | Omni access (already connected in the pipeline) |

**Known limitation of the PoC:** the three parsed streams are scoped slices (pricing and billing, mobile and login, prospects). Core-workflow feedback from existing customers is under-represented until the full-population phase, and the dashboard states this plainly.

## The doc set

| Doc | Covers |
|---|---|
| `01-brief.md` | This page: why, who, goals |
| `02-current-state.md` | What exists in the repo today and the data issues found |
| `03-data-model.md` | Notes, requests, areas, assignments, aggregates |
| `04-ranking.md` | How requests are scored and the dashboard's sort lenses |
| `05-build-plan.md` | How it's built into the local browser, milestone by milestone |
| `requests.yaml` | The draft taxonomy of canonical requests (to curate) |
| `notes.seed.jsonl`, `assignments.draft.jsonl` | Seed data so the UI can be built immediately |
