"""notes.jsonl + assignments.jsonl + taxonomy -> aggregates.json. Pure code, no model calls —
see docs/03-data-model.md (the Aggregate entity) and docs/04-ranking.md (the scoring).

M1 scope: friction score (intensity x source x account, persistence-boosted), the ingredients
next to it (companies/notes/weeks/intensity mix/streams), and per-request evidence for the
drawer. M2 adds trend: each request's all-time-cumulative rank as of 1 reported week ago, 3
reported weeks ago, and ~90 days ago (a real calendar cutoff, unlike the two week-count
snapshots — the pipeline's own OCS convention is also 91-day rolling, see behavioral.py).
The CURRENT rank stays all-time cumulative over every reported week, per the brief: "for now."
"""
from __future__ import annotations

import json
import re
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
NOTES = ROOT / "data" / "notes.jsonl"
ASSIGNMENTS = ROOT / "data" / "assignments.jsonl"
REQUESTS_YAML = ROOT / "taxonomy" / "requests.yaml"
RANKING_YAML = ROOT / "taxonomy" / "ranking.yaml"
OVERRIDES_YAML = ROOT / "data" / "overrides.yaml"
OUT = ROOT / "data" / "aggregates.json"

WEEK_RE = re.compile(r"(\d{4})-W(\d{1,2})")


def load_jsonl(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as f:
        return [json.loads(ln) for ln in f if ln.strip()]


def company_key(note: dict) -> str:
    """A distinct company, or the contact when the company didn't resolve (03-data-model.md)."""
    company = note.get("company")
    if company and company != "unknown":
        return company
    return f"contact:{note.get('contact') or note['note_id']}"


def resolve_assignments(assignments: list[dict], overrides: dict) -> dict[str, set]:
    """note_id -> set(request_id), with hand overrides always winning."""
    by_note = defaultdict(set)
    for a in assignments:
        by_note[a["note_id"]].add(a["request_id"])
    for note_id, ov in (overrides.get("overrides") or {}).items():
        for rid in ov.get("add", []):
            by_note[note_id].add(rid)
        for rid in ov.get("remove", []):
            by_note[note_id].discard(rid)
    return by_note


def week_sort_key(label: str) -> tuple:
    m = WEEK_RE.match(label)
    return (int(m.group(1)), int(m.group(2))) if m else (0, 0)


def week_monday(label: str) -> date | None:
    """The Monday of a note's ISO week label — enough to place a report week on a real
    calendar for the 90-day cutoff. `2026-W32` is a multi-week catch-up bucket (02-current-
    state.md); this dates it at ISO week 32's Monday, same approximation the rest of the
    pipeline already makes by keying everything off the label."""
    m = WEEK_RE.match(label)
    return date.fromisocalendar(int(m.group(1)), int(m.group(2)), 1) if m else None


def _weight_fns(ranking: dict):
    w_intensity = ranking["weights"]["intensity"]
    w_source = ranking["weights"]["source"]
    w_account = ranking["weights"]["account"]

    def intensity_weight(note: dict) -> float:
        return w_intensity.get(note.get("intensity", "mild"), 1)

    def source_weight(note: dict) -> float:
        # Not in the Note schema until the `md` adapter (M4) — no-op until then.
        if "unprompted" not in note:
            return 1
        return w_source["volunteered"] if note["unprompted"] else w_source["convened"]

    def account_weight(note: dict) -> float:
        # Not in the Note schema until M4 — no-op until then.
        lifecycle = note.get("lifecycle")
        if lifecycle is None:
            return 1
        if lifecycle == "paying" and note.get("archetype") in ("Ghost", "Struggler"):
            return w_account.get("paying_at_risk", 1)
        return w_account.get(lifecycle, 1)

    return intensity_weight, source_weight, account_weight


def group_by_request(notes: dict, note_to_requests: dict, requests_by_id: dict,
                      weeks_subset: set | None = None) -> dict[str, dict[str, list]]:
    """request_id -> company_key -> [note, ...], optionally restricted to a set of weeks —
    the one grouping step every ranking (current or a historical snapshot) is built from."""
    by_request: dict[str, dict[str, list]] = defaultdict(lambda: defaultdict(list))
    for note_id, req_ids in note_to_requests.items():
        note = notes.get(note_id)
        if not note:
            continue
        if weeks_subset is not None and note["week"] not in weeks_subset:
            continue
        ck = company_key(note)
        for rid in req_ids:
            if rid not in requests_by_id:
                continue
            by_request[rid][ck].append(note)
    return by_request


def rank_snapshot(by_request: dict, weeks_in_range: int, min_companies: int, max_boost: float,
                   intensity_weight, source_weight, account_weight) -> dict[str, int]:
    """request_id -> rank, for one weeks-subset snapshot. Same formula as the live board
    (04-ranking.md) so a historical rank is directly comparable to the current one — omits
    anything under the min-companies guardrail, same rule as the live board's "Emerging" cutoff."""
    scored = []
    for rid, companies in by_request.items():
        if len(companies) < min_companies:
            continue
        company_weight_sum = 0.0
        weeks_present: set[str] = set()
        for ns in companies.values():
            strongest = max(ns, key=intensity_weight)
            company_weight_sum += intensity_weight(strongest) * source_weight(strongest) * account_weight(strongest)
            weeks_present.update(n["week"] for n in ns)
        persistence_mult = 1 + max_boost * (len(weeks_present) / weeks_in_range if weeks_in_range else 0)
        scored.append((rid, company_weight_sum * persistence_mult))
    scored.sort(key=lambda x: -x[1])
    return {rid: i for i, (rid, _) in enumerate(scored, 1)}


def main() -> None:
    notes = {n["note_id"]: n for n in load_jsonl(NOTES)}
    assignments = load_jsonl(ASSIGNMENTS)
    requests_doc = yaml.safe_load(REQUESTS_YAML.read_text(encoding="utf-8"))
    ranking = yaml.safe_load(RANKING_YAML.read_text(encoding="utf-8"))
    overrides = yaml.safe_load(OVERRIDES_YAML.read_text(encoding="utf-8")) or {}

    areas_by_id = {a["id"]: a["name"] for a in requests_doc["areas"]}
    requests_by_id = {r["id"]: r for r in requests_doc["requests"]}
    note_to_requests = resolve_assignments(assignments, overrides)

    all_weeks_set = {n["week"] for n in notes.values()}
    weeks_sorted = sorted(all_weeks_set, key=week_sort_key)
    weeks_in_range = len(weeks_sorted)
    min_companies = ranking["guardrails"]["min_companies"]
    intensity_weight, source_weight, account_weight = _weight_fns(ranking)

    # ── the live board: all-time cumulative over every reported week ("for now" — see brief) ──
    by_request = group_by_request(notes, note_to_requests, requests_by_id)
    skipped_unknown_request = {rid for note_id, req_ids in note_to_requests.items()
                                for rid in req_ids if rid not in requests_by_id}

    results = []
    for rid, req in requests_by_id.items():
        companies = by_request.get(rid, {})
        req_notes = [n for ns in companies.values() for n in ns]

        company_weight_sum = 0.0
        for ns in companies.values():
            strongest = max(ns, key=intensity_weight)
            company_weight_sum += intensity_weight(strongest) * source_weight(strongest) * account_weight(strongest)

        weeks_present = sorted(set(n["week"] for n in req_notes))
        persistence_mult = 1 + ranking["persistence"]["max_boost"] * (
            len(weeks_present) / weeks_in_range if weeks_in_range else 0)
        friction_score = round(company_weight_sum * persistence_mult, 2)

        intensity_mix = {"mild": 0, "strong": 0, "churn-threatening": 0}
        sentiment_mix = {"positive": 0, "neutral": 0, "negative": 0}
        streams_present: set[str] = set()
        for n in req_notes:
            intensity_mix[n.get("intensity", "mild")] += 1
            sentiment_mix[n.get("sentiment", "neutral")] += 1
            streams_present.update(n.get("streams", []))

        evidence = [
            {
                "note_id": n["note_id"], "week": n["week"],
                "company": n.get("company", "unknown"), "contact": n.get("contact"),
                "streams": sorted(set(n.get("streams", []))),
                "summary": n.get("summary", {}),
                "sentiment": n.get("sentiment"), "intensity": n.get("intensity"),
            }
            for n in sorted(req_notes, key=lambda n: n["week"])
        ]

        results.append({
            "id": rid, "name": req["name"], "area": req["area"],
            "area_name": areas_by_id.get(req["area"], req["area"]), "kind": req["kind"],
            "companies": len(companies), "notes": len(req_notes),
            "weeks_present": len(weeks_present), "weeks_in_range": weeks_in_range,
            "intensity_mix": intensity_mix, "sentiment_mix": sentiment_mix,
            "streams_present": sorted(streams_present),
            "friction_score": friction_score,
            "ranked": len(companies) >= min_companies,
            "evidence": evidence,
        })

    ranked = sorted((r for r in results if r["ranked"]), key=lambda r: -r["friction_score"])
    emerging = sorted((r for r in results if not r["ranked"]), key=lambda r: -r["companies"])
    for i, r in enumerate(ranked, 1):
        r["rank"] = i

    # ── trend: the same all-time cumulative ranking, snapshotted at 3 earlier boundaries ──────
    # "1 week ago" / "3 weeks ago" count REPORTED weeks (there are real gaps — 02-current-
    # state.md), not calendar weeks. "90 days ago" is the one calendar-based cutoff, so it can
    # land between two reported weeks; we use the most recent week still outside that window.
    def snapshot_weeks(n_weeks_back: int) -> set | None:
        if len(weeks_sorted) <= n_weeks_back:
            return None
        return set(weeks_sorted[:-n_weeks_back])

    snap_90d = None
    if weeks_sorted:
        cutoff = week_monday(weeks_sorted[-1]) - timedelta(days=90)
        candidate = [w for w in weeks_sorted if (week_monday(w) or cutoff) <= cutoff]
        if candidate and len(candidate) < len(weeks_sorted):
            snap_90d = set(candidate)

    trend_snapshots = {"1w": snapshot_weeks(1), "3w": snapshot_weeks(3), "90d": snap_90d}
    trend_ranks = {}
    for key, subset in trend_snapshots.items():
        if subset is None:
            trend_ranks[key] = {}
            continue
        snap_by_request = group_by_request(notes, note_to_requests, requests_by_id, subset)
        trend_ranks[key] = rank_snapshot(snap_by_request, len(subset), min_companies,
                                          ranking["persistence"]["max_boost"],
                                          intensity_weight, source_weight, account_weight)

    for r in results:
        r["trend"] = {key: ranks.get(r["id"]) for key, ranks in trend_ranks.items()}

    unlabeled = [nid for nid in notes if nid not in note_to_requests or not note_to_requests[nid]]

    out = {
        "generated_from": {
            "notes": str(NOTES.relative_to(ROOT)), "assignments": str(ASSIGNMENTS.relative_to(ROOT)),
            "taxonomy_version": requests_doc.get("version"), "ranking_version": ranking.get("version"),
        },
        "coverage": {
            "notes": len(notes),
            "streams": sorted({s for n in notes.values() for s in n.get("streams", [])}),
            "weeks": weeks_sorted,
            "unlabeled_notes": len(unlabeled),
        },
        "trend_availability": {k: (v is not None) for k, v in trend_snapshots.items()},
        "ranked": ranked,
        "emerging": emerging,
    }
    OUT.write_text(json.dumps(out, indent=2), encoding="utf-8")
    if skipped_unknown_request:
        print(f"  [aggregate] dropped {len(skipped_unknown_request)} request_id(s) not in "
              f"requests.yaml: {sorted(skipped_unknown_request)}")
    print(f"wrote {OUT} ({len(ranked)} ranked, {len(emerging)} emerging, "
          f"{len(notes)} notes, {len(unlabeled)} unlabeled)")


if __name__ == "__main__":
    main()
