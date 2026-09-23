"""VoC Dashboard — a single self-contained static site: a readable per-report browser plus
a master trend dashboard on top. Scans reports/<stream>/{weekly,monthly,quarterly}/*.md,
renders each to HTML (same content, same tables, typeset for reading), and writes one static
page with a sidebar nav. No server, no dependencies: open index.html directly in a browser,
or deploy it as-is (this repo commits the built index.html at the root for exactly that).

This is a sanitized demo mirror — see README.md for what that means and its known limits.
The master dashboard (visibility/scripts/build_site.py) is mounted as this site's homepage —
the "one site, dig deeper if needed" shape described in visibility/docs/01-brief.md — with
the per-report browser one click away in the same sidebar.
"""
import html
import importlib.util
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "index.html"

import design_tokens  # Terra (Ninety's design system) tokens — see that module's docstring

DASHBOARD_AGGREGATES = ROOT / "visibility" / "data" / "aggregates.json"
_dashboard_src = ROOT / "visibility" / "scripts" / "build_site.py"
dashboard = None
if _dashboard_src.exists():
    _spec = importlib.util.spec_from_file_location("visibility_dashboard", _dashboard_src)
    dashboard = importlib.util.module_from_spec(_spec)
    _spec.loader.exec_module(dashboard)

STREAMS = [
    ("commercial-engine", "Commercial Engine"),
    ("mobile", "Mobile"),
    ("pre-sales", "Pre-sales"),
]
PERIODS = [("weekly", "Weekly"), ("monthly", "Monthly"), ("quarterly", "Quarterly")]

META_RE = re.compile(
    r"<!--\s*feedback-intel:\s*audience=(?P<audience>\S+)\s+period=(?P<period>\S+)\s+"
    r"label=(?P<label>\S+)\s+window_from=(?P<wf>\S+)\s+window_to=(?P<wt>\S+)\s*-->"
)

SENT = {"positive": "pos", "negative": "neg", "neutral": "neu"}
INT = {"churn-threatening": "churn", "strong": "strong", "mild": "mild", "unknown": "unknown"}


# ── markdown → HTML (faithful to the .md, not a general-purpose parser) ────────────────────
def inline(t: str) -> str:
    t = html.escape(t)
    t = re.sub(r"`([^`]+)`", r"<code>\1</code>", t)
    t = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", t)
    t = re.sub(r"(?<!\*)\*(?!\*)([^*\n]+?)(?<!\*)\*(?!\*)", r"<em>\1</em>", t)
    return t


def sent_int_cell(raw: str) -> str:
    parts = [p.strip() for p in raw.split("·")]
    out = []
    for p in parts:
        word = re.sub(r"[*]", "", p).strip()
        if word in SENT:
            out.append(f'<span class="sent sent-{SENT[word]}">{html.escape(word)}</span>')
        elif word in INT:
            out.append(f'<span class="chip int-{INT[word]}">{html.escape(word)}</span>')
        else:
            out.append(inline(p))
    return " ".join(out)


def render_table(rows: list[str]) -> str:
    cells = [[c.strip() for c in r.strip().strip("|").split("|")] for r in rows]
    header = cells[0]
    body = cells[2:]  # skip the separator row
    seg_i = header.index("Segment") if "Segment" in header else -1
    si_i = header.index("Sentiment · Intensity") if "Sentiment · Intensity" in header else -1
    co_i = header.index("Company") if "Company" in header else -1
    who_i = header.index("Who") if "Who" in header else -1
    rank = header[0] == "#"
    th = "".join(f"<th>{inline(h)}</th>" for h in header)
    trs = []
    for r in body:
        # An unresolved company has no reliable identity attached — the literal word "unknown"
        # next to a contact name reads like a bug, not a fact. Blank both rather than assert
        # an identity the pipeline itself couldn't resolve.
        unresolved = co_i != -1 and r[co_i] == "unknown"
        tds = []
        for i, c in enumerate(r):
            if i == 0 and rank:
                tds.append(f'<td class="rank"><span>{html.escape(c)}</span></td>')
            elif i == co_i and unresolved:
                tds.append('<td class="co">—</td>')
            elif i == who_i and unresolved:
                tds.append('<td>—</td>')
            elif i == seg_i:
                tds.append(f'<td><span class="chip seg">{html.escape(c)}</span></td>')
            elif i == si_i:
                tds.append(f'<td class="si-cell">{sent_int_cell(c)}</td>')
            else:
                cls = ' class="co"' if i == co_i else ""
                tds.append(f"<td{cls}>{inline(c)}</td>")
        trs.append("<tr>" + "".join(tds) + "</tr>")
    return (f'<div class="tbl-wrap"><table><thead><tr>{th}</tr></thead>'
            f'<tbody>{"".join(trs)}</tbody></table></div>')


def render_body(md: str) -> str:
    lines = md.splitlines()
    out, i, n = [], 0, len(lines)
    while i < n:
        ln = lines[i]
        s = ln.strip()
        if not s:
            i += 1
            continue
        if s.startswith("#### "):
            out.append(f"<h4>{inline(s[5:])}</h4>")
            i += 1
            continue
        if s.startswith("### "):
            out.append(f"<h3>{inline(s[4:])}</h3>")
            i += 1
            continue
        if s.startswith("## "):
            out.append(f"<h2>{inline(s[3:])}</h2>")
            i += 1
            continue
        if s.startswith("# "):
            out.append(f'<h1 class="rpt-title">{inline(s[2:])}</h1>')
            i += 1
            continue
        if s == "---":
            out.append('<hr class="foot-rule">')
            i += 1
            continue
        if s.startswith("**The week in one line:**"):
            rest = s[len("**The week in one line:**"):].strip()
            out.append(f'<div class="verdict"><span class="verdict-k">The week in one line</span>'
                       f'<p>{inline(rest)}</p></div>')
            i += 1
            continue
        if s.startswith(">"):
            out.append(f'<blockquote>{inline(s.lstrip("> "))}</blockquote>')
            i += 1
            continue
        if s.startswith("|"):
            blk = []
            while i < n and lines[i].strip().startswith("|"):
                blk.append(lines[i])
                i += 1
            out.append(render_table(blk))
            continue
        if re.match(r"^\d+\.\s", s):
            items = []
            while i < n and re.match(r"^\d+\.\s", lines[i].strip()):
                item_text = re.sub(r"^\d+\.\s", "", lines[i].strip())
                items.append(f"<li>{inline(item_text)}</li>")
                i += 1
            out.append(f"<ol>{''.join(items)}</ol>")
            continue
        if s.startswith("- "):
            items = []
            while i < n and lines[i].strip().startswith("- "):
                items.append(f"<li>{inline(lines[i].strip()[2:])}</li>")
                i += 1
            out.append(f"<ul>{''.join(items)}</ul>")
            continue
        cls = ' class="note"' if s.startswith("*") and s.endswith("*") and not s.startswith("**") else ""
        out.append(f"<p{cls}>{inline(s)}</p>")
        i += 1
    return "\n".join(out)


# ── scan every report on disk ────────────────────────────────────────────────────────────────
def week_sort_key(label: str) -> int:
    m = re.search(r"W(\d+)", label)
    return int(m.group(1)) if m else 0


entries = []
for slug, disp in STREAMS:
    for pkey, pdisp in PERIODS:
        d = ROOT / "reports" / slug / pkey
        if not d.is_dir():
            continue
        for p in sorted(d.glob("*.md")):
            text = p.read_text(encoding="utf-8")
            m = META_RE.search(text)
            meta = m.groupdict() if m else {}
            label = meta.get("label", p.stem)
            lines = text.splitlines()
            start = next((idx for idx, ln in enumerate(lines) if ln.strip().startswith("# ")), 0)
            body_md = "\n".join(lines[start:])
            entries.append({
                "id": f"{slug}-{pkey}-{label}".replace(".", "-"),
                "stream_slug": slug, "stream": disp,
                "period_key": pkey, "period": pdisp,
                "label": label,
                "wf": meta.get("wf", ""), "wt": meta.get("wt", ""),
                "churn": "churn-threatening" in text,
                "html": render_body(body_md),
            })

if not entries:
    raise SystemExit("No report files found — run this from a checkout with report dirs populated.")

overall_latest = max(entries, key=lambda e: (e["wt"], e["label"]))

dashboard_data = None
if dashboard is not None and DASHBOARD_AGGREGATES.exists():
    dashboard_data = json.loads(DASHBOARD_AGGREGATES.read_text(encoding="utf-8"))
default_active_id = "master-dashboard" if dashboard_data else overall_latest["id"]

# ── nav (grouped by stream, then by period, newest first) ──────────────────────────────────
nav_html, cards = [], []
if dashboard_data:
    dash_nav, dash_section = dashboard.render_dashboard(dashboard_data)
    nav_html.append(dash_nav)
    cards.append(dash_section)
for slug, disp in STREAMS:
    stream_entries = [e for e in entries if e["stream_slug"] == slug]
    if not stream_entries:
        continue
    periods_present = [pk for pk, _ in PERIODS if any(e["period_key"] == pk for e in stream_entries)]
    contains_active = any(e["id"] == default_active_id for e in stream_entries)
    collapsed_cls = "" if contains_active else " collapsed"
    group = [f'<div class="nav-stream{collapsed_cls}" data-stream="{slug}">',
             f'<div class="nav-group"><span>{disp}</span><span class="chev">▾</span></div>']
    for pkey, pdisp in PERIODS:
        pe = [e for e in stream_entries if e["period_key"] == pkey]
        if not pe:
            continue
        if pkey == "weekly":
            pe.sort(key=lambda e: week_sort_key(e["label"]), reverse=True)
        else:
            pe.sort(key=lambda e: e["label"], reverse=True)
        if len(periods_present) > 1:
            group.append(f'<div class="nav-period">{pdisp}</div>')
        for e in pe:
            active = " active" if e["id"] == default_active_id else ""
            dot = ('<span class="churn-dot" title="a churn-threatening note in this report">'
                   '</span>') if e["churn"] else ""
            short_label = e["label"].replace("2026-", "")
            search_key = f"{disp} {pdisp} {e['label']}".lower()
            group.append(
                f'<button class="nav-item{active}" data-target="{e["id"]}" '
                f'data-search="{html.escape(search_key)}">'
                f'<span class="ni-wk">{html.escape(short_label)}</span>'
                f'<span class="ni-meta">{e["wf"][5:10]}{dot}</span></button>')
    group.append("</div>")
    nav_html.append("\n".join(group))

    for e in stream_entries:
        active = " active" if e["id"] == default_active_id else ""
        window = f'{e["wf"][:10]} → {e["wt"][:10]} UTC' if e["wf"] else ""
        cards.append(
            f'<section class="report{active}" id="{e["id"]}">'
            f'<div class="rpt-eyebrow">{disp} <span class="sep">/</span> {e["period"]} '
            f'<span class="sep">/</span> {window}</div>'
            f'{e["html"]}</section>')

STYLE = """
<style>
""" + design_tokens.ROOT_CSS + """
*{box-sizing:border-box}
html,body{margin:0;background:var(--bg)}
.wrap{background:var(--bg);color:var(--ink);font-family:var(--font-body);line-height:1.55;
  min-height:100vh;-webkit-font-smoothing:antialiased}
.topbar{position:sticky;top:0;z-index:10;background:color-mix(in srgb,var(--bg) 88%,transparent);
  backdrop-filter:blur(8px);border-bottom:1px solid var(--border);padding:14px clamp(16px,4vw,40px);
  display:flex;align-items:baseline;justify-content:space-between;gap:16px;flex-wrap:wrap}
.brand{font-family:var(--font-heading);font-size:1.15rem;font-weight:600;letter-spacing:.01em;
  display:flex;align-items:center;gap:9px}
.brand-logo{height:22px;width:auto;display:block}
.tag{font-family:var(--font-mono);font-size:.7rem;text-transform:uppercase;letter-spacing:.12em;
  color:var(--ink-3)}
.layout{display:grid;grid-template-columns:250px minmax(0,1fr);gap:0;align-items:start}
.rail{position:sticky;top:57px;align-self:stretch;max-height:calc(100vh - 57px);overflow-y:auto;
  border-right:1px solid var(--border);padding:14px 14px 40px}
.search-box{width:100%;padding:8px 10px;margin-bottom:10px;border:1px solid var(--border);
  border-radius:8px;background:var(--surface);color:var(--ink);font-family:var(--font-body);
  font-size:.85rem}
.search-box:focus{outline:none;border-color:var(--accent)}
.nav-group{font-family:var(--font-mono);font-size:.68rem;text-transform:uppercase;letter-spacing:.14em;
  color:var(--ink-3);margin:18px 8px 6px;cursor:pointer;user-select:none;
  display:flex;align-items:center;justify-content:space-between;gap:6px}
.nav-group:hover{color:var(--ink-2)}
.nav-group .chev{font-size:.65rem;transition:transform .15s}
.nav-stream.collapsed .nav-group .chev{transform:rotate(-90deg)}
.nav-stream.collapsed .nav-period,
.nav-stream.collapsed .nav-item{display:none}
.nav-stream:first-of-type .nav-group{margin-top:0}
.nav-period{font-family:var(--font-body);font-size:.72rem;font-weight:600;color:var(--ink-2);
  margin:8px 10px 2px}
.nav-item{display:flex;align-items:center;justify-content:space-between;width:100%;gap:8px;
  background:none;border:1px solid transparent;border-radius:8px;padding:7px 10px;cursor:pointer;
  color:var(--ink-2);font-family:var(--font-body);font-size:.87rem;text-align:left;transition:.15s}
.nav-item:hover{background:var(--surface-2);color:var(--ink)}
.nav-item.active{background:var(--accent-soft);border-color:var(--border);color:var(--ink);font-weight:600}
.ni-wk{font-variant-numeric:tabular-nums;display:inline-flex;align-items:center;gap:7px}
.nav-icon{height:14px;width:14px;display:block;opacity:.7}
.ni-meta{font-family:var(--font-mono);font-size:.66rem;color:var(--ink-3);display:flex;align-items:center;gap:6px}
.churn-dot{width:7px;height:7px;border-radius:50%;background:var(--churn);display:inline-block}
.main{padding:clamp(20px,3.5vw,44px) clamp(16px,4vw,56px) 96px;max-width:1040px}
.report{display:none;animation:fade .2s ease}
.report.active{display:block}
@keyframes fade{from{opacity:0;transform:translateY(4px)}to{opacity:1;transform:none}}
@media (prefers-reduced-motion:reduce){.report{animation:none}}
.rpt-eyebrow{font-family:var(--font-mono);font-size:.72rem;text-transform:uppercase;letter-spacing:.1em;
  color:var(--accent-2);margin-bottom:10px}
.rpt-eyebrow .sep{color:var(--ink-3);margin:0 4px}
.rpt-title{font-family:var(--font-heading);font-size:1.5rem;margin:0 0 16px;text-wrap:balance}
.verdict{background:var(--surface);border:1px solid var(--border);border-left:3px solid var(--accent);
  border-radius:8px;padding:16px 20px;margin:14px 0 30px}
.verdict-k{display:block;font-family:var(--font-mono);font-size:.68rem;text-transform:uppercase;
  letter-spacing:.14em;color:var(--ink-3);margin-bottom:6px}
.verdict p{margin:0;font-family:var(--font-heading);font-size:1.24rem;line-height:1.42;color:var(--ink);
  text-wrap:balance}
h1,h2,h3,h4{color:var(--ink)}
h2{font-family:var(--font-heading);font-size:1.28rem;font-weight:600;margin:34px 0 12px;
  padding-bottom:7px;border-bottom:1px solid var(--border);letter-spacing:.01em;text-wrap:balance}
h3{font-family:var(--font-body);font-size:.95rem;font-weight:700;margin:24px 0 8px;text-wrap:balance}
h4{font-family:var(--font-mono);font-size:.72rem;text-transform:uppercase;letter-spacing:.14em;
  color:var(--ink-3);font-weight:600;margin:20px 0 8px}
ul,ol{margin:0 0 12px;padding-left:0;list-style:none;display:flex;flex-direction:column;gap:9px}
ol{counter-reset:ol-counter}
ul li{position:relative;padding-left:20px;color:var(--ink-2)}
ul li::before{content:"";position:absolute;left:4px;top:.62em;width:6px;height:6px;border-radius:50%;
  background:var(--accent);opacity:.55}
ol li{position:relative;padding-left:26px;color:var(--ink-2);counter-increment:ol-counter}
ol li::before{content:counter(ol-counter)".";position:absolute;left:0;top:0;font-family:var(--font-mono);
  font-weight:700;color:var(--accent-2);font-size:.85rem}
li strong{color:var(--ink)}
code{font-family:var(--font-mono);font-size:.86em;background:var(--surface-2);padding:1px 5px;
  border-radius:4px;color:var(--accent-2)}
.tbl-wrap{overflow-x:auto;border:1px solid var(--border);border-radius:8px;box-shadow:var(--shadow-1);margin:6px 0 16px;
  background:var(--surface)}
table{border-collapse:collapse;width:100%;font-size:.9rem;min-width:560px}
thead th{text-align:left;font-family:var(--font-mono);font-size:.66rem;text-transform:uppercase;
  letter-spacing:.09em;color:var(--ink-3);font-weight:600;padding:11px 14px;
  border-bottom:1px solid var(--border);background:var(--sink);white-space:nowrap}
tbody td{padding:11px 14px;border-bottom:1px solid var(--border-2);color:var(--ink-2);
  vertical-align:top}
tbody tr:last-child td{border-bottom:none}
td.co{color:var(--ink);font-weight:600;white-space:nowrap}
td.rank span{display:inline-flex;align-items:center;justify-content:center;width:22px;height:22px;
  border-radius:4px;background:var(--accent-soft);color:var(--accent-2);font-family:var(--font-mono);
  font-size:.78rem;font-weight:700;font-variant-numeric:tabular-nums}
.chip{display:inline-block;font-family:var(--font-mono);font-size:.7rem;letter-spacing:.02em;
  padding:2px 8px;border-radius:999px;white-space:nowrap;border:1px solid transparent}
.chip.seg{background:var(--surface-2);color:var(--ink-2);border-color:var(--border)}
.si-cell{white-space:nowrap}
.sent{font-family:var(--font-mono);font-size:.76rem}
.sent-pos{color:var(--pos)} .sent-neg{color:var(--neg)} .sent-neu{color:var(--neu)}
.int-churn{background:var(--churn-bg);color:var(--churn);border-color:color-mix(in srgb,var(--churn) 30%,transparent);font-weight:700}
.int-strong{background:var(--strong-bg);color:var(--strong);border-color:color-mix(in srgb,var(--strong) 26%,transparent)}
.int-mild{background:var(--mild-bg);color:var(--mild)}
.int-unknown{background:var(--surface-2);color:var(--ink-3)}
.foot-rule{border:none;border-top:1px solid var(--border);margin:36px 0 8px}
p{margin:0 0 12px;max-width:74ch}
.note{font-size:.86rem;color:var(--ink-3);background:var(--sink);border:1px solid var(--border-2);
  border-radius:8px;padding:10px 14px}
.report h3 + ul li{font-family:var(--font-mono);font-size:.8rem;color:var(--ink-3)}
.report h3 + ul li strong{color:var(--ink-2)}
blockquote{margin:0 0 12px;padding:8px 14px;border-left:3px solid var(--strong);
  background:var(--strong-bg);border-radius:0 8px 8px 0;color:var(--ink-2);font-size:.9rem}
@media (max-width:820px){
  .layout{grid-template-columns:1fr}
  .rail{position:static;max-height:none;border-right:none;border-bottom:1px solid var(--border);
    padding:12px clamp(16px,4vw,40px)}
}
</style>
"""
if dashboard_data:
    STYLE = STYLE.replace("</style>", dashboard.DASHBOARD_CSS + "</style>")

SCRIPT = """
<script>
(function(){
  const items = document.querySelectorAll('.nav-item');
  const reports = document.querySelectorAll('.report');
  const streams = document.querySelectorAll('.nav-stream');
  items.forEach(function(btn){
    btn.addEventListener('click', function(){
      const t = btn.dataset.target;
      items.forEach(function(b){ b.classList.toggle('active', b === btn); });
      reports.forEach(function(r){ r.classList.toggle('active', r.id === t); });
      document.querySelector('.main').scrollTo({top: 0, behavior: 'instant'});
    });
  });
  document.querySelectorAll('.nav-group').forEach(function(g){
    g.addEventListener('click', function(){
      g.closest('.nav-stream').classList.toggle('collapsed');
    });
  });
  const search = document.getElementById('nav-search');
  let savedCollapse = null;   // collapse state as the user left it, captured when a search starts
  search.addEventListener('input', function(){
    const terms = search.value.trim().toLowerCase().split(/\\s+/).filter(Boolean);
    if (terms.length && savedCollapse === null) {
      savedCollapse = new Map();
      streams.forEach(function(g){ savedCollapse.set(g, g.classList.contains('collapsed')); });
    }
    items.forEach(function(b){
      b.style.display = terms.every(function(t){ return b.dataset.search.includes(t); }) ? '' : 'none';
    });
    streams.forEach(function(g){
      const anyVisible = Array.from(g.querySelectorAll('.nav-item'))
        .some(function(b){ return b.style.display !== 'none'; });
      g.style.display = anyVisible ? '' : 'none';
      g.classList.toggle('collapsed', terms.length ? !anyVisible
        : (savedCollapse ? savedCollapse.get(g) : g.classList.contains('collapsed')));
    });
    if (!terms.length) { savedCollapse = null; }
  });
})();
</script>
"""
if dashboard_data:
    SCRIPT = SCRIPT + f"<script>{dashboard.DASHBOARD_SCRIPT}</script>"

HTML = f"""<!doctype html>
<html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>VoC Dashboard</title>
{design_tokens.FONT_LINKS}
{STYLE}
</head><body>
<div class="wrap">
  <div class="topbar">
    <div class="brand"><img src="assets/ninety-logo.svg" class="brand-logo" alt="Ninety"> VoC Dashboard</div>
    <div class="tag">Concept demo &middot; sanitized data &middot; static snapshot, not live</div>
  </div>
  <div class="layout">
    <nav class="rail">
      <input id="nav-search" class="search-box" type="text" placeholder="Filter (stream, period, week)…">
      {''.join(nav_html)}
    </nav>
    <main class="main">{''.join(cards)}</main>
  </div>
</div>
{SCRIPT}
</body></html>
"""

OUT.write_text(HTML, encoding="utf-8")
print(f"wrote {OUT} ({len(HTML)} bytes, {len(entries)} reports)")
