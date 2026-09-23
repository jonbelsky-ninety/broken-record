"""aggregates.json -> the master dashboard nav entry + section.

Two ways this gets used:
  1. Imported by scratch/build_site.py, which mounts the dashboard as the homepage of the
     unified local site (nav entry + section, sharing that page's CSS/JS shell).
  2. Run directly (`python3 scripts/build_site.py`) for a quick standalone look at
     visibility/site/index.html, wrapped in its own minimal page shell.

Either way the content is identical — `render_dashboard()` is the single source of truth.
Sparklines/filters are M2 (see docs/05-build-plan.md); the trend column landed here.
"""
from __future__ import annotations

import html
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
AGGREGATES = ROOT / "data" / "aggregates.json"
OUT = ROOT / "site" / "index.html"

_SCRATCH_DIR = ROOT.parent / "scratch"
if str(_SCRATCH_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRATCH_DIR))
import design_tokens  # Terra (Ninety's design system) tokens — see that module's docstring

KIND_LABEL = {"defect": "Defect", "gap": "Gap", "confusion": "Confusion",
              "pricing": "Pricing", "integration": "Integration", "adoption": "Adoption"}
STREAM_SHORT = {"commercial-engine": "CE", "mobile": "MO", "pre-sales": "PS",
                "ninetyio": "NIO", "skunkworks": "SW"}

# CSS classes this view needs that aren't already part of the shared report-browser palette
# (scratch/build_site.py's STYLE) — kept small and additive on purpose, see the module docstring.
DASHBOARD_CSS = """
.req-row{cursor:pointer}
.req-row:hover{background:var(--surface-2)}
.req-row.open{background:var(--accent-soft)}
td.req-name div:first-child{color:var(--ink);font-weight:600}
.req-area{font-size:.74rem;color:var(--ink-3);margin-top:2px}
td.num{font-variant-numeric:tabular-nums;text-align:right;white-space:nowrap}
td.score{font-weight:700;color:var(--accent-2)}
.chip.stream{background:var(--surface-2);color:var(--ink-3);margin-right:3px}
.kind-defect{background:var(--churn-bg);color:var(--churn);border-color:transparent}
.kind-gap{background:var(--surface-2);color:var(--ink-2)}
.kind-confusion{background:var(--strong-bg);color:var(--strong);border-color:transparent}
.kind-pricing{background:var(--accent-soft);color:var(--accent-2);border-color:transparent}
.kind-integration{background:var(--surface-2);color:var(--ink-2)}
.kind-adoption{background:var(--surface-2);color:var(--ink-2)}
.mix .im{display:inline-block;font-family:var(--font-mono);font-size:.68rem;margin-right:6px;white-space:nowrap}
.im-churn{color:var(--churn);font-weight:700}
.im-strong{color:var(--strong)}
.im-mild{color:var(--ink-3)}
.ev-row td{padding:0;border-bottom:1px solid var(--border-2)}
.ev-wrap{background:var(--sink);padding:14px 20px;display:flex;flex-direction:column;gap:10px}
.ev-item{background:var(--surface);border:1px solid var(--border-2);border-radius:8px;padding:10px 14px}
.ev-head{display:flex;align-items:center;gap:10px;flex-wrap:wrap;margin-bottom:4px}
.ev-co{font-weight:700;color:var(--ink)}
.ev-contact{color:var(--ink-3);font-size:.82rem}
.ev-week{font-family:var(--font-mono);font-size:.7rem;color:var(--ink-3);background:var(--surface-2);
  padding:1px 6px;border-radius:4px}
.ev-summary{font-size:.86rem;color:var(--ink-2)}
.emerging-note{font-size:.8rem;color:var(--ink-3);margin:-4px 0 10px}
td.trend-cell{font-variant-numeric:tabular-nums;text-align:right;white-space:nowrap;color:var(--ink-2)}
td.trend-cell.muted{color:var(--ink-3);text-align:center}
.trend-arrow{display:inline-block;margin-right:3px;font-size:.72rem}
.trend-up{color:var(--pos)}
.trend-down{color:var(--churn)}
.trend-flat{color:var(--ink-3)}
.chip.trend-new{background:var(--accent-soft);color:var(--accent-2);border-color:transparent}
"""

# Row expand/collapse — independent of (and coexists with) the report-browser's nav-item toggle.
DASHBOARD_SCRIPT = """
(function(){
  document.querySelectorAll('.req-row').forEach(function(row){
    row.addEventListener('click', function(){
      var ev = document.getElementById(row.dataset.target);
      var open = ev.style.display !== 'none';
      ev.style.display = open ? 'none' : '';
      row.classList.toggle('open', !open);
    });
  });
})();
"""


def chip(text: str, cls: str) -> str:
    return f'<span class="chip {cls}">{html.escape(text)}</span>'


def intensity_mix_html(mix: dict) -> str:
    parts = []
    if mix.get("churn-threatening"):
        parts.append(f'<span class="im im-churn">{mix["churn-threatening"]} churn</span>')
    if mix.get("strong"):
        parts.append(f'<span class="im im-strong">{mix["strong"]} strong</span>')
    if mix.get("mild"):
        parts.append(f'<span class="im im-mild">{mix["mild"]} mild</span>')
    return " ".join(parts) or '<span class="im im-mild">—</span>'


def stream_chips(streams: list) -> str:
    return " ".join(chip(STREAM_SHORT.get(s, s), "stream") for s in streams)


def evidence_row(rid: str, evidence: list) -> str:
    items = []
    for e in evidence:
        summary = " ".join(f"<strong>{html.escape(k)}:</strong> {html.escape(v)}"
                            for k, v in e.get("summary", {}).items())
        intensity = e.get("intensity", "mild")
        int_cls = {"churn-threatening": "churn"}.get(intensity, intensity)
        # An unresolved company has no reliable identity attached to it — showing the literal
        # word "unknown" next to a contact name reads like a bug, not a fact. Drop both rather
        # than assert an identity the pipeline itself couldn't resolve.
        company = e["company"]
        id_line = (
            f'<span class="ev-co">{html.escape(company)}</span>'
            f'<span class="ev-contact">{html.escape(e.get("contact") or "")}</span>'
            if company != "unknown" else ""
        )
        items.append(
            '<div class="ev-item">'
            f'<div class="ev-head">{id_line}'
            f'<span class="ev-week">{html.escape(e["week"])}</span>'
            f'{stream_chips(e["streams"])}'
            f'<span class="sent sent-{e.get("sentiment", "neutral")[:3]}">{html.escape(e.get("sentiment", ""))}</span>'
            f'{chip(intensity, "int-" + int_cls)}'
            '</div>'
            f'<div class="ev-summary">{summary}</div>'
            '</div>'
        )
    return (f'<tr class="ev-row" id="ev-{rid}" style="display:none">'
            f'<td colspan="12"><div class="ev-wrap">{"".join(items)}</div></td></tr>')


def trend_cell(rank_now: int | None, hist_rank: int | None, available: bool) -> str:
    if not available:
        return '<td class="trend-cell muted" title="not enough report history yet">–</td>'
    if hist_rank is None:
        return '<td class="trend-cell"><span class="chip trend-new">New</span></td>'
    if rank_now is None:
        return f'<td class="trend-cell num">{hist_rank}</td>'
    if rank_now < hist_rank:
        arrow, cls = "▲", "trend-up"
    elif rank_now > hist_rank:
        arrow, cls = "▼", "trend-down"
    else:
        arrow, cls = "–", "trend-flat"
    return f'<td class="trend-cell num"><span class="trend-arrow {cls}">{arrow}</span>{hist_rank}</td>'


def table_row(r: dict, rank_col: bool, trend_availability: dict) -> str:
    rank_cell = f'<td class="rank"><span>{r["rank"]}</span></td>' if rank_col else '<td class="rank"><span>—</span></td>'
    rank_now = r.get("rank")
    trend = r.get("trend", {})
    return (
        f'<tr class="req-row" data-target="ev-{r["id"]}">'
        f'{rank_cell}'
        f'<td class="req-name"><div>{html.escape(r["name"])}</div>'
        f'<div class="req-area">{html.escape(r["area_name"])}</div></td>'
        f'<td>{chip(KIND_LABEL.get(r["kind"], r["kind"]), "kind-" + r["kind"])}</td>'
        f'<td class="num score">{r["friction_score"]}</td>'
        f'{trend_cell(rank_now, trend.get("1w"), trend_availability.get("1w", False))}'
        f'{trend_cell(rank_now, trend.get("3w"), trend_availability.get("3w", False))}'
        f'{trend_cell(rank_now, trend.get("90d"), trend_availability.get("90d", False))}'
        f'<td class="num">{r["companies"]}</td>'
        f'<td class="num">{r["notes"]}</td>'
        f'<td class="num">{r["weeks_present"]}/{r["weeks_in_range"]}</td>'
        f'<td class="mix">{intensity_mix_html(r["intensity_mix"])}</td>'
        f'<td class="streams">{stream_chips(r["streams_present"])}</td>'
        '</tr>'
    )


def render_dashboard(data: dict) -> tuple[str, str]:
    """(nav_html, section_html) for id="master-dashboard" — the single source both the
    standalone page and the unified report-browser site mount."""
    trend_availability = data.get("trend_availability", {})
    ranked_rows, ranked_ev = [], []
    for r in data["ranked"]:
        ranked_rows.append(table_row(r, rank_col=True, trend_availability=trend_availability))
        ranked_ev.append(evidence_row(r["id"], r["evidence"]))

    emerging_rows, emerging_ev = [], []
    for r in data["emerging"]:
        emerging_rows.append(table_row(r, rank_col=False, trend_availability=trend_availability))
        emerging_ev.append(evidence_row(r["id"], r["evidence"]))

    nav_html = (
        '<div class="nav-stream" data-stream="overview">'
        '<div class="nav-group"><span>Overview</span><span class="chev">▾</span></div>'
        '<button class="nav-item active" data-target="master-dashboard" '
        'data-search="overview master dashboard friction ranking">'
        '<span class="ni-wk"><img src="assets/dashboard-icon.svg" class="nav-icon" alt=""> Overview</span></button>'
        '</div>'
    )

    trend_head = '<th title="rank 1 reported week ago">1 Wk</th><th title="rank 3 reported weeks ago">3 Wks</th><th title="rank ~90 days ago">90 Days</th>'
    empty_row = '<tr><td colspan="12">None right now.</td></tr>'
    section_html = f"""
<section class="report active" id="master-dashboard">
  <h1 class="rpt-title">Overview</h1>
  <h2>Stack rank &middot; sorted by friction score (all-time)</h2>
  <div class="tbl-wrap">
    <table>
      <thead><tr>
        <th>#</th><th>Request</th><th>Kind</th><th>Score</th>{trend_head}<th>Cos.</th><th>Notes</th>
        <th>Weeks</th><th>Intensity</th><th>Streams</th>
      </tr></thead>
      <tbody>{"".join(r for pair in zip(ranked_rows, ranked_ev) for r in pair)}</tbody>
    </table>
  </div>
  <h2>Emerging &middot; fewer than 3 companies (not yet ranked)</h2>
  <p class="emerging-note">Listed by companies, not scored — a single loud note can't take a top slot.</p>
  <div class="tbl-wrap">
    <table>
      <thead><tr>
        <th>#</th><th>Request</th><th>Kind</th><th>Score</th>{trend_head}<th>Cos.</th><th>Notes</th>
        <th>Weeks</th><th>Intensity</th><th>Streams</th>
      </tr></thead>
      <tbody>{"".join(r for pair in zip(emerging_rows, emerging_ev) for r in pair) if emerging_rows else empty_row}</tbody>
    </table>
  </div>
</section>
"""
    return nav_html, section_html


# ── standalone mode: a minimal page shell around the same content, for a quick look ─────────
_SHELL_CSS = design_tokens.ROOT_CSS + """
*{box-sizing:border-box}
html,body{margin:0;background:var(--bg)}
body{color:var(--ink);font-family:var(--font-body);line-height:1.5;-webkit-font-smoothing:antialiased}
.topbar{position:sticky;top:0;z-index:10;background:color-mix(in srgb,var(--bg) 88%,transparent);
  backdrop-filter:blur(8px);border-bottom:1px solid var(--border);padding:16px clamp(16px,4vw,40px)}
.brand{font-family:var(--font-heading);font-size:1.3rem;font-weight:600}
.brand em{color:var(--accent);font-style:normal}
.main{padding:clamp(16px,3vw,36px) clamp(16px,4vw,40px) 80px;max-width:1180px;margin:0 auto}
.report{display:block}
.rpt-title{font-family:var(--font-heading);font-size:1.5rem;margin:0 0 16px}
h2{font-family:var(--font-heading);font-size:1.15rem;font-weight:600;margin:32px 0 10px}
.tbl-wrap{overflow-x:auto;border:1px solid var(--border);border-radius:8px;box-shadow:var(--shadow-1);background:var(--surface)}
table{border-collapse:collapse;width:100%;font-size:.87rem;min-width:900px}
thead th{text-align:left;font-family:var(--font-mono);font-size:.64rem;text-transform:uppercase;
  letter-spacing:.08em;color:var(--ink-3);font-weight:600;padding:10px 12px;
  border-bottom:1px solid var(--border);background:var(--sink);white-space:nowrap}
tbody td{padding:10px 12px;border-bottom:1px solid var(--border-2);color:var(--ink-2);vertical-align:top}
td.rank span{display:inline-flex;align-items:center;justify-content:center;width:22px;height:22px;
  border-radius:4px;background:var(--accent-soft);color:var(--accent-2);font-family:var(--font-mono);
  font-size:.76rem;font-weight:700}
.chip{display:inline-block;font-family:var(--font-mono);font-size:.66rem;padding:2px 7px;
  border-radius:999px;white-space:nowrap;border:1px solid var(--border)}
.sent{font-family:var(--font-mono);font-size:.72rem}
.sent-pos{color:var(--pos)} .sent-neg{color:var(--neg)} .sent-neu{color:var(--neu)}
"""


def main() -> None:
    data = json.loads(AGGREGATES.read_text(encoding="utf-8"))
    _, section_html = render_dashboard(data)
    html_out = f"""<!doctype html>
<html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>VoC Dashboard</title>
{design_tokens.FONT_LINKS}
<style>{_SHELL_CSS}{DASHBOARD_CSS}
.brand{{display:flex;align-items:center;gap:9px}}
.brand-logo{{height:22px;width:auto;display:block}}
</style>
</head><body>
<div class="topbar"><div class="brand"><img src="assets/ninety-logo.svg" class="brand-logo" alt="Ninety"> VoC Dashboard</div></div>
<div class="main">{section_html}</div>
<script>{DASHBOARD_SCRIPT}</script>
</body></html>
"""
    OUT.parent.mkdir(exist_ok=True)
    assets_dir = OUT.parent / "assets"
    assets_dir.mkdir(exist_ok=True)
    logo_src = _SCRATCH_DIR / "assets" / "ninety-logo.svg"
    if logo_src.exists():
        (assets_dir / "ninety-logo.svg").write_bytes(logo_src.read_bytes())
    OUT.write_text(html_out, encoding="utf-8")
    print(f"wrote {OUT} ({len(html_out)} bytes, {len(data['ranked'])} ranked, {len(data['emerging'])} emerging)")
    print("Note: this is a standalone preview. The real homepage is scratch/index.html "
          "(rebuild with scratch/build_site.py), which mounts this dashboard as its landing page.")


if __name__ == "__main__":
    main()
