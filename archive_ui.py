"""Archive UI pieces shared by generate_dashboard.py and the archive page.

- render_calendar_html(): a server-rendered month calendar (works without
  JavaScript) for the live dashboards, linking each archived day to the viewer.
- write_archive_page(): writes data/dashboard/archive.html, a static page that
  reads data/archive/index/*.json and the archived files in the browser.
  Nothing is rendered per day, so the repo does not grow with pages.
"""
from __future__ import annotations

import calendar
import json
from datetime import date
from pathlib import Path

from site_common import BANNER_HTML, PRIVACY_NOTE, SUPPORT_HTML

INDEX_DIR = Path("data/archive/index")
PLOTLY_SRC = "https://cdn.plot.ly/plotly-4.1.1.min.js"  # same build the live dashboards load

ARCHIVE_CSS = """
    .archive-cal { max-width: 850px; margin: 16px auto 30px; background:#003c82; border-radius:10px;
      padding: 15px 20px 20px; box-shadow: 0 0 10px rgba(0,0,0,0.3); }
    .archive-cal h2 { margin: 0 0 4px; font-size: 1.2em; text-align:center; text-transform: uppercase; }
    .archive-cal .intro { text-align:center; margin: 0 0 12px; font-size: 0.95em; color:#e0e0e0; }
    .cal-grid { display:flex; flex-wrap:wrap; gap: 20px; }
    .cal-month { flex: 1 1 300px; }
    .cal-head { display:flex; align-items:center; justify-content:space-between; margin: 6px 0 8px; }
    .cal-head .cal-title { font-weight: 700; font-size: 1.1em; }
    .cal-head button, .cal-head a.cal-step { background:white; color:#0054ad; border:2px solid white; border-radius:6px;
      font-weight:700; padding:4px 12px; cursor:pointer; font-size:0.95em; }
    .cal-head button:disabled { opacity: .35; cursor: default; }
    table.cal { width:100%; border-collapse: separate; border-spacing: 4px; table-layout: fixed; }
    table.cal caption { caption-side: top; font-weight:700; padding-bottom:6px; }
    table.cal th { font-size: .85em; color:#d9eaff; font-weight:600; }
    table.cal td { padding:0; height: 2.6em; }
    .cal-day { display:flex; align-items:center; justify-content:center; height:100%; border-radius:6px;
      background:#0054ad; color:white; font-weight:600; border:2px solid transparent; }
    a.cal-day:hover, button.cal-day:hover { background:#d9eaff; color:#003c82; }
    button.cal-day { width:100%; font: inherit; cursor:pointer; }
    .cal-none { display:flex; align-items:center; justify-content:center; height:100%; color:#ffffff55; }
    .cal-day.in-window { background:#2f74c8; }
    .cal-day.selected { background:white; color:#003c82; border-color:#FFD140; }
    .cal-day.today-live { outline: 2px dashed #ffffff88; outline-offset: -4px; }
    .cal-legend { display:flex; flex-wrap:wrap; gap:14px; justify-content:center; list-style:none; padding:0;
      margin:10px 0 0; font-size:.85em; color:#e0e0e0; }
    .swatch { display:inline-block; width:12px; height:12px; border-radius:3px; margin-right:5px; vertical-align:-1px; }
    .vh { position:absolute; width:1px; height:1px; overflow:hidden; clip:rect(0 0 0 0); white-space:nowrap; }
    .archive-more { text-align:center; margin: 12px 0 0; }
    .archive-more a { text-decoration: underline; }
    .archive-notice { max-width: 850px; margin: 10px auto 0; background:#FFD140; color:#1a1a1a;
      border-radius:10px; padding: 12px 18px; line-height:1.45em; box-shadow: 0 0 10px rgba(0,0,0,0.3); }
    .archive-notice strong.pill { display:inline-block; background:#1a1a1a; color:#FFD140; border-radius:4px;
      padding:1px 8px; margin-right:8px; letter-spacing:.06em; font-size:.85em; }
    .archive-notice a { color:#003c82; text-decoration: underline; font-weight:700; }
    .window-box { max-width: 850px; margin: 16px auto; border:2px solid #ffffff66; border-radius:10px;
      padding: 12px 18px; line-height:1.5em; }
    .window-box dl { display:grid; grid-template-columns: max-content 1fr; gap: 2px 14px; margin:0; }
    .window-box dt { font-weight:700; }
    .window-box dd { margin:0; }
    .runs { display:flex; flex-wrap:wrap; gap:8px; justify-content:center; margin: 6px 0 0; }
    .runs button { background:#0054ad; color:white; border:2px solid #ffffff88; border-radius:6px; padding:5px 10px;
      cursor:pointer; font: inherit; font-size:.9em; }
    .runs button[aria-pressed="true"] { background:white; color:#003c82; border-color:#FFD140; font-weight:700; }
    .nav-buttons button.nav-btn { font: inherit; font-weight:600; cursor:pointer; }
    .muted { color:#d9eaff; font-size:.9em; }
    @media (max-width: 600px) {
      .window-box dl { grid-template-columns: 1fr; }
      table.cal { border-spacing: 2px; }
      body { padding: 12px !important; }
    }
"""


def _load_months() -> dict[str, dict[str, int]]:
    f = INDEX_DIR / "months.json"
    if not f.exists():
        return {}
    return {m["month"]: m["days"] for m in json.loads(f.read_text(encoding="utf-8"))["months"]}


def _month_table(key: str, days: dict[str, int], period_label: str) -> str:
    y, m = map(int, key.split("-"))
    rows = []
    for week in calendar.Calendar(firstweekday=6).monthdatescalendar(y, m):  # Sunday first, like FAPD
        cells = []
        for d in week:
            if d.month != m:
                cells.append("<td></td>")
                continue
            iso, long = d.isoformat(), d.strftime("%A, %B %-d, %Y")
            if iso in days:
                cells.append(
                    f'<td><a class="cal-day" href="archive.html?d={iso}&amp;w={period_label}">{d.day}'
                    f'<span class="vh"> — archived summaries for {long}</span></a></td>'
                )
            else:
                cells.append(f'<td><span class="cal-none">{d.day}<span class="vh"> — nothing archived for {long}</span></span></td>')
        rows.append("<tr>" + "".join(cells) + "</tr>")
    heads = "".join(f'<th scope="col"><abbr title="{n}">{n[:2]}</abbr></th>'
                    for n in ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"])
    name = date(y, m, 1).strftime("%B %Y")
    return (f'<div class="cal-month"><table class="cal"><caption>{name} '
            f'<span class="muted">({len(days)} {"day" if len(days) == 1 else "days"} archived)</span></caption>'
            f'<thead><tr>{heads}</tr></thead><tbody>{"".join(rows)}</tbody></table></div>')


def render_calendar_html(today_la: date, period_label: str) -> str:
    """Last two archived months for the live dashboards (no JavaScript needed).

    Each archived day links to archive.html?d=<day>&w=<period>, so a visitor on
    the 7-day dashboard lands on that day's 7-day window.
    """
    months = _load_months()
    keys = [k for k in sorted(months) if k <= today_la.strftime("%Y-%m")][-2:]
    if not keys:
        return ""
    tables = "".join(_month_table(k, months[k], period_label) for k in reversed(keys))
    return f"""
  <nav class="archive-cal" aria-label="Past summaries">
    <h2>Past Days &amp; Periods</h2>
    <p class="intro">Every update is archived. Pick a day to see its 4-hour, 1-day, 7-day, 30-day and 90-day
      views exactly as they were published, each labelled with the time window it covers.</p>
    <div class="cal-grid">{tables}</div>
    <p class="archive-more"><a href="archive.html?w={period_label}">Open the full archive (all months)</a></p>
  </nav>
"""


ARCHIVE_PAGE = r"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Hustle Long Beach Dashboard — Archive</title>
  <meta name="robots" content="noindex, follow">
  <style>
__BASE_CSS__
__ARCHIVE_CSS__
  </style>
  <script charset="utf-8" src="__PLOTLY_SRC__"></script>
</head>
<body>
__BANNER_HTML__
  <h1 id="page-title">City Service Dashboard — Archive</h1>

  <div class="archive-notice" role="note" id="archive-notice">
    <strong class="pill">ARCHIVE</strong>
    You are viewing a <strong>past snapshot</strong>, not current data. Numbers and the written summary are exactly
    as they were published at the time shown below; cases the City updated later are not reflected.
    <a href="index_24hours.html">Go to the current dashboard</a>
  </div>

  <noscript><div class="window-box">The archive is drawn in your browser and needs JavaScript, like the charts on the
    <a href="index_24hours.html">current dashboard</a>. The raw archived files are public in the
    <a href="https://github.com/davidkarnowski/HustleYourCity/tree/main/data/archive">project repository</a>.</div></noscript>
  <div class="nav-buttons" role="group" aria-label="Time window" id="window-tabs"></div>

  <section class="archive-cal" aria-label="Choose a day">
    <div class="cal-head">
      <button type="button" id="prev-month" aria-label="Previous month">&larr;</button>
      <span class="cal-title" id="cal-title">…</span>
      <button type="button" id="next-month" aria-label="Next month">&rarr;</button>
    </div>
    <table class="cal" id="cal"><thead><tr>
      <th scope="col"><abbr title="Sunday">Su</abbr></th><th scope="col"><abbr title="Monday">Mo</abbr></th>
      <th scope="col"><abbr title="Tuesday">Tu</abbr></th><th scope="col"><abbr title="Wednesday">We</abbr></th>
      <th scope="col"><abbr title="Thursday">Th</abbr></th><th scope="col"><abbr title="Friday">Fr</abbr></th>
      <th scope="col"><abbr title="Saturday">Sa</abbr></th></tr></thead><tbody id="cal-body"></tbody></table>
    <ul class="cal-legend">
      <li><span class="swatch" style="background:white;border:2px solid #FFD140"></span>Selected day</li>
      <li><span class="swatch" style="background:#2f74c8"></span>Days covered by the selected window</li>
      <li><span class="swatch" style="background:#0054ad;border:1px solid #fff5"></span>Archived day</li>
    </ul>
    <p class="muted" style="text-align:center;margin:10px 0 0">Snapshots taken that day (Pacific time). The last one is shown by default:</p>
    <div class="runs" id="runs" role="group" aria-label="Snapshot time"></div>
  </section>

  <div class="window-box" id="window-box" aria-live="polite"></div>

  <div class="status-box">
    <div class="status-title" id="status-title">Archived Status Update</div>
    <div class="status-text" id="status-text">Loading…</div>
  </div>

  <div id="chart"></div>
  <br>
  <div id="table"></div>

__SUPPORT_HTML__
  <div class="footer">
    <p>Disclaimer: This dashboard is generated automatically from Long Beach’s public service request dataset via the Go Long Beach app. Accuracy depends on city data quality and parsing reliability.</p>
    <p>Archived views are rebuilt in your browser from the snapshot files saved by each four-hour update. The written summaries were produced by an AI model at the time and are shown unedited.</p>
    <p>Project Source: <a href="https://github.com/davidkarnowski/HustleYourCity" target="_blank">HustleYourCity on GitHub</a></p>
    <div class="privacy-note">__PRIVACY_NOTE__</div>
  </div>

<script>
(() => {
  const ARCHIVE = "../archive/";
  const TZ = "America/Los_Angeles";
  const WINDOWS = {
    "4hours":  {key: "Last 4 Hours", label: "4 Hours", hours: 4,    phrase: "4 hours"},
    "24hours": {key: "Last 1 Days",  label: "1 Day",   hours: 24,   phrase: "24 hours"},
    "7days":   {key: "Last 7 Days",  label: "7 Days",  hours: 168,  phrase: "7 days"},
    "30days":  {key: "Last 30 Days", label: "30 Days", hours: 720,  phrase: "30 days"},
    "90days":  {key: "Last 90 Days", label: "90 Days", hours: 2160, phrase: "90 days"},
  };
  const state = {months: [], monthCache: {}, w: "24hours", day: null, runId: null, run: null, viewMonth: null};

  const fmt = (iso, opts) => new Intl.DateTimeFormat("en-US", {timeZone: TZ, ...opts}).format(new Date(iso));
  const fmtFull = iso => fmt(iso, {weekday: "long", year: "numeric", month: "long", day: "numeric",
                                   hour: "numeric", minute: "2-digit", timeZoneName: "short"});
  const fmtShort = iso => fmt(iso, {month: "short", day: "numeric", year: "numeric", hour: "numeric",
                                    minute: "2-digit", timeZoneName: "short"});
  const fmtTime = iso => fmt(iso, {hour: "numeric", minute: "2-digit", timeZoneName: "short"});
  const laDate = iso => fmt(iso, {year: "numeric", month: "2-digit", day: "2-digit"}).replace(/(\d+)\/(\d+)\/(\d+)/, "$3-$1-$2");
  const longDay = d => new Date(d + "T12:00:00Z").toLocaleDateString("en-US", {timeZone: "UTC", weekday: "long", month: "long", day: "numeric", year: "numeric"});
  const esc = s => s.replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));

  // Index files change every run, so revalidate them; archived snapshot files never change.
  const isIndex = p => p.includes("/index/");
  async function getJSON(p) { const r = await fetch(p, {cache: isIndex(p) ? "no-cache" : "default"}); if (!r.ok) throw new Error(p + " " + r.status); return r.json(); }
  async function getText(p) { const r = await fetch(p); if (!r.ok) throw new Error(p + " " + r.status); return r.text(); }
  // The window ends when the run computed it (window_end); older index files only have downloaded_at.
  const endOf = run => run.window_end || run.downloaded_at;

  async function monthRuns(m) {
    if (!state.monthCache[m]) state.monthCache[m] = getJSON(`${ARCHIVE}index/${m}.json`).then(j => j.runs).catch(() => []);
    return state.monthCache[m];
  }
  const daysIn = m => (state.months.find(x => x.month === m) || {days: {}}).days;

  function normalizeStatus(s) {
    const t = s.trim().toLowerCase();
    if (t.includes("duplicate")) return null;
    if (t.includes("closed")) return "Closed";
    if (t.includes("in progress")) return "In Progress";
    if (t.includes("open")) return "Open";
    return s.replace(/\w\S*/g, w => w[0].toUpperCase() + w.slice(1).toLowerCase());
  }

  function syncURL(push) {
    const q = new URLSearchParams({d: state.day, w: state.w});
    if (state.runId) q.set("run", state.runId);
    const url = "?" + q.toString();
    if (url === location.search) return;
    push ? history.pushState(null, "", url) : history.replaceState(null, "", url);
  }
  function readURL() {
    const q = new URLSearchParams(location.search);
    state.w = WINDOWS[q.get("w")] ? q.get("w") : "24hours";
    const all = state.months.flatMap(x => Object.keys(x.days)).sort();
    // Default: the most recent *complete* Pacific day, never "today", so the archive never looks like the live page.
    const todayLA = laDate(new Date().toISOString());
    const past = all.filter(d => d < todayLA);
    state.day = all.includes(q.get("d")) ? q.get("d") : (past[past.length - 1] || all[all.length - 1]);
    state.runId = q.get("run");
  }
  window.addEventListener("popstate", () => { readURL(); render(false); });

  function renderTabs() {
    const box = document.getElementById("window-tabs");
    box.innerHTML = "";
    for (const [k, v] of Object.entries(WINDOWS)) {
      const b = document.createElement("button");
      b.type = "button"; b.className = "nav-btn" + (k === state.w ? " nav-btn-active" : "");
      b.textContent = v.label; b.setAttribute("aria-pressed", k === state.w);
      b.onclick = () => { state.w = k; render(true); };
      box.appendChild(b);
    }
    const a = document.createElement("a");
    a.href = `index_${state.w}.html`; a.className = "nav-btn"; a.textContent = "Current";
    box.appendChild(a);
    const ab = document.createElement("a");
    ab.href = "about.html"; ab.className = "nav-btn"; ab.textContent = "About";
    box.appendChild(ab);
  }

  function renderCalendar(run) {
    const m = state.viewMonth, days = daysIn(m);
    const [y, mo] = m.split("-").map(Number);
    document.getElementById("cal-title").textContent =
      new Date(Date.UTC(y, mo - 1, 15)).toLocaleDateString("en-US", {timeZone: "UTC", month: "long", year: "numeric"});
    const idx = state.months.findIndex(x => x.month === m);
    document.getElementById("prev-month").disabled = idx <= 0;
    document.getElementById("next-month").disabled = idx >= state.months.length - 1;

    // Window coverage: from (snapshot - window) to snapshot, in LA calendar days.
    let from = null, to = null;
    if (run) {
      const end = new Date(endOf(run));
      to = laDate(endOf(run));
      from = laDate(new Date(end - WINDOWS[state.w].hours * 3600e3).toISOString());
    }
    const first = new Date(Date.UTC(y, mo - 1, 1)), startDow = first.getUTCDay();
    const nDays = new Date(Date.UTC(y, mo, 0)).getUTCDate();
    const body = document.getElementById("cal-body");
    body.innerHTML = "";
    let tr = document.createElement("tr");
    for (let i = 0; i < startDow; i++) tr.appendChild(document.createElement("td"));
    for (let d = 1; d <= nDays; d++) {
      const iso = `${m}-${String(d).padStart(2, "0")}`;
      const td = document.createElement("td");
      if (days[iso]) {
        const b = document.createElement("button");
        b.type = "button"; b.className = "cal-day";
        if (from && iso >= from && iso <= to) b.classList.add("in-window");
        if (iso === state.day) { b.classList.add("selected"); b.setAttribute("aria-current", "date"); }
        b.innerHTML = `${d}<span class="vh"> — ${longDay(iso)}, ${days[iso]} snapshots</span>`;
        b.onclick = () => { state.day = iso; state.runId = null; render(true); };
        td.appendChild(b);
      } else {
        td.innerHTML = `<span class="cal-none">${d}<span class="vh"> — nothing archived for ${longDay(iso)}</span></span>`;
      }
      tr.appendChild(td);
      if ((startDow + d) % 7 === 0) { body.appendChild(tr); tr = document.createElement("tr"); }
    }
    if (tr.children.length) body.appendChild(tr);
  }

  function renderRuns(dayRuns, run) {
    const box = document.getElementById("runs");
    box.innerHTML = "";
    for (const r of dayRuns) {
      const b = document.createElement("button");
      b.type = "button"; b.textContent = fmtTime(endOf(r));
      b.setAttribute("aria-pressed", r.id === run.id);
      b.onclick = () => { state.runId = r.id; render(true); };
      box.appendChild(b);
    }
  }

  // The City publishes every few hours; requests created after its last publish were not in the data yet,
  // so the newest part of every window is empty. Say how much (audit 2026-11-01: totals match the City's
  // current data exactly up to the publish time).
  function gapNote(run, end, w) {
    if (!run.data_processed_at) return "";
    const gapMin = Math.round((new Date(end) - new Date(run.data_processed_at)) / 60000);
    if (gapMin < 10) return "";
    const h = Math.floor(gapMin / 60), m = gapMin % 60;
    const len = (h ? `${h} h ` : "") + `${m} min`;
    const all = gapMin >= w.hours * 60;
    return `<dt>Not yet in City data</dt><dd>Requests created after ${esc(fmtTime(run.data_processed_at))} were not yet published
      by the City, so the last ${len} of this window ${all ? "(all of it)" : ""} show no requests. They appear in later snapshots.</dd>`;
  }

  function renderWindow(run) {
    const w = WINDOWS[state.w];
    const end = endOf(run), start = new Date(new Date(end) - w.hours * 3600e3).toISOString();
    const endDay = longDay(laDate(end));
    document.getElementById("page-title").textContent = `City Service Dashboard — ${w.label} ending ${endDay} (Archived)`;
    document.title = `Hustle Long Beach — ${w.label} ending ${endDay} (Archived)`;
    document.getElementById("window-box").innerHTML = `<dl>
      <dt>Window</dt><dd>The ${w.phrase} ending <strong>${esc(fmtFull(end))}</strong><br>
        <span class="muted">${esc(fmtShort(start))} → ${esc(fmtShort(end))}, by the date each request was created</span></dd>
      <dt>City data as of</dt><dd>${run.data_processed_at ? esc(fmtFull(run.data_processed_at)) + " (when the City last published the dataset)" : "Not recorded for this early snapshot"}</dd>
      ${gapNote(run, end, w)}
      <dt>Downloaded by this site</dt><dd>${run.downloaded_at_exact ? esc(fmtFull(run.downloaded_at)) : "Not recorded for this early snapshot"}</dd>
    </dl>`;
    document.getElementById("status-title").textContent = `Archived Status Update — ${w.label} ending ${endDay}`;
  }

  async function renderData(run, stale) {
    const w = WINDOWS[state.w];
    const textEl = document.getElementById("status-text");
    const tp = run.texts[state.w];
    if (tp) {
      try {
        let t = (await getText(ARCHIVE + tp)).trim();
        if (stale()) return;
        if (t.length > 2000) t = t.slice(0, 2000) + "...";
        const fb = run.fallback.includes(state.w)
          ? "<em class='muted'>At the time of this snapshot the AI service was unavailable, so the site re-showed an earlier summary. It is reproduced here as it appeared.</em>\n\n" : "";
        textEl.innerHTML = fb + esc(t);
      } catch { textEl.textContent = "(The archived summary for this snapshot could not be loaded.)"; }
    } else {
      textEl.textContent = "(No written summary was archived for this snapshot. Written summaries are archived from late November 2025; the numbers below are still from this snapshot.)";
    }

    let data;
    try { data = await getJSON(ARCHIVE + run.json); if (stale()) return; }
    catch { document.getElementById("chart").innerHTML = "<p style='text-align:center'>Snapshot data could not be loaded.</p>"; return; }
    const types = (data[w.key] || {}).types || {};
    const endDay = longDay(laDate(endOf(run)));
    const avg = [], table = {};
    for (const [t, v] of Object.entries(types)) {
      if (!v || typeof v !== "object" || t.toLowerCase().includes("duplicate")) continue;
      if (v.avg_response_hours != null) avg.push([t, v.avg_response_hours]);
      const sc = {};
      for (const [k, n] of Object.entries(v.status_counts || {})) { const s = normalizeStatus(k); if (s) sc[s] = (sc[s] || 0) + Number(n); }
      if (Object.keys(sc).length) table[t] = sc;
    }
    avg.sort((a, b) => b[1] - a[1]);
    const chartEl = document.getElementById("chart");
    if (avg.length) {
      Plotly.react(chartEl, [{type: "bar", orientation: "h", y: avg.map(x => x[0]), x: avg.map(x => x[1]), marker: {color: "#ffffff"},
        hovertemplate: "%{y}: %{x:.1f} hours<extra></extra>"}], {
        title: {text: `Average Response Time (Hours) — ${w.label} ending ${endDay} · ARCHIVED`},
        xaxis: {title: {text: "Hours"}, gridcolor: "#ffffff33"}, yaxis: {title: {text: "Service Type"}},
        plot_bgcolor: "#0054ad", paper_bgcolor: "#0054ad", font: {color: "white"},
        margin: {l: 180, r: 50, t: 80, b: 50}, height: Math.max(400, 30 * avg.length + 200)}, {responsive: true, displaylogo: false});
    } else {
      Plotly.purge(chartEl);
      chartEl.innerHTML = "<p style='text-align:center;font-size:1.2em;margin:40px 0;'>No average response time data for this period.</p>";
    }
    const tableEl = document.getElementById("table");
    const names = Object.keys(table);
    if (names.length) {
      const statuses = [...new Set(names.flatMap(n => Object.keys(table[n])))].sort();
      const cols = statuses.map(s => names.map(n => table[n][s] || 0));
      const totals = names.map(n => statuses.reduce((a, s) => a + (table[n][s] || 0), 0));
      Plotly.react(tableEl, [{type: "table",
        header: {values: ["Service Type", ...statuses, "Total"], fill: {color: "#003c82"}, font: {color: "white", size: 13}, align: "left", height: 28},
        cells: {values: [names, ...cols, totals], fill: {color: [names.map((_, i) => i % 2 ? "#0054ad" : "#004b9b")]}, font: {color: "white", size: 12}, align: "left", height: 22}}],
        {title: {text: `Service Call Status Breakdown — ${w.label} ending ${endDay} · ARCHIVED`}, plot_bgcolor: "#0054ad", paper_bgcolor: "#0054ad",
         font: {color: "white"}, margin: {l: 30, r: 30, t: 40, b: 10}, height: Math.max(160, 66 + 28 + names.length * 22)}, {displaylogo: false});
    } else {
      Plotly.purge(tableEl);
      tableEl.innerHTML = `<p style='text-align:center;font-size:1.2em;margin:40px 0;'>No service request data found for this period.</p>`;
    }
  }

  let renderSeq = 0;
  async function render(push) {
    const seq = ++renderSeq;
    const stale = () => seq !== renderSeq;
    renderTabs();
    const m = state.day.slice(0, 7);
    // A day's runs can sit in its own month index only (the index is keyed by Pacific date).
    const dayRuns = (await monthRuns(m)).filter(r => r.date_la === state.day)
      .sort((a, b) => endOf(a).localeCompare(endOf(b)));
    if (stale()) return;
    if (!state.viewMonth || !state.months.some(x => x.month === state.viewMonth)) state.viewMonth = m;
    if (!dayRuns.length) { renderCalendar(null); document.getElementById("status-text").textContent = "Nothing archived for that day."; return; }
    const run = dayRuns.find(r => r.id === state.runId) || dayRuns[dayRuns.length - 1];
    state.runId = run.id === dayRuns[dayRuns.length - 1].id ? null : run.id;  // default run stays out of the URL
    state.viewMonth = m;
    state.run = run;
    syncURL(push);
    renderCalendar(run); renderRuns(dayRuns, run); renderWindow(run);
    await renderData(run, stale);
  }

  document.getElementById("prev-month").onclick = () => step(-1);
  document.getElementById("next-month").onclick = () => step(1);
  function step(n) {
    const i = state.months.findIndex(x => x.month === state.viewMonth) + n;
    if (i < 0 || i >= state.months.length) return;
    state.viewMonth = state.months[i].month;
    // Keep the selection; just page the calendar.
    renderCalendar(state.run || null);
  }

  (async () => {
    try { state.months = (await getJSON(ARCHIVE + "index/months.json")).months; }
    catch { document.getElementById("status-text").textContent = "The archive index could not be loaded."; return; }
    readURL();
    await render(false);
  })();
})();
</script>
</body>
</html>
"""


def write_archive_page(base_css: str, out: Path = Path("data/dashboard/archive.html")) -> Path:
    html = (ARCHIVE_PAGE.replace("__BASE_CSS__", base_css)
            .replace("__BANNER_HTML__", "  " + BANNER_HTML)
            .replace("__SUPPORT_HTML__", SUPPORT_HTML)
            .replace("__PRIVACY_NOTE__", PRIVACY_NOTE)
            .replace("__ARCHIVE_CSS__", ARCHIVE_CSS)
            .replace("__PLOTLY_SRC__", PLOTLY_SRC))
    out.parent.mkdir(parents=True, exist_ok=True)
    if not out.exists() or out.read_text(encoding="utf-8") != html:  # static page: commit only when it changes
        out.write_text(html, encoding="utf-8")
    return out
