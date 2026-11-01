# CLAUDE.md

Operational guide for AI assistants working in this repository. Keep this file lean — link out to the deep evaluation doc for narrative.

> **Companion document:** a long-form architecture review, gap analysis and roadmap is kept in the
> maintainer's private project notes (outside this repository). Ask the maintainer before proposing
> structural changes.

---

## What this project is

**Hustle Long Beach** (`HustleYourCity`) is a static, automation-driven civic-accountability dashboard. Every four hours it pulls the City of Long Beach's public 311 / "Go Long Beach" service-request dataset, computes per-type response-time metrics across rolling time windows, generates a natural-language summary with an LLM, renders five HTML dashboards plus PNG charts, and commits the artifacts back to the repo. GitHub Pages serves the result at <https://hustlelongbeach.com>.

There is **no server**, **no database**, and **no application backend** — the entire system is a Python pipeline orchestrated by GitHub Actions, with the git repo doubling as the data store.

---

## Pipeline at a glance

```
City of Long Beach Open Data API  (Opendatasoft / Huwise v2.1)
            │
            ▼
  full_exporter.py  ──►  data/service_requests_full_<UTC>.json.gz   (~11–12 MB)
            │
            ▼
  type_status_response_summary.py  ──►  data/summary_results_current.json
                                         data/archive/YYYY/MM/summary_json_*.json
            │
            ▼
  LLM_inference.py  (Google Gemini 3.1 Flash-Lite Preview)
            │   reads summary JSON, writes 5 timeframe text files:
            ▼
  data/current_{4_hour|24_hour|7_day|30_day|90_day}_text_status.txt
            │
            ▼
  build_archive_index.py  ──►  data/archive/index/<YYYY-MM>.json + months.json
            │                   (pairs each archived run's JSON with its 5 texts; Pacific-date keyed)
            ▼
  generate_dashboard.py  ──►  data/dashboard/index_{4hours|24hours|7days|30days|90days}.html
       │  (calls generate_charts.py for PNG branding overlay)
       ├─►  data/charts/average_response_<period>.png
       └─►  data/dashboard/archive.html  (static archive viewer; renders past runs in the browser)
            │
            ▼
  generate_about_page.py  ──►  data/dashboard/about.html  (rendered from README.md)
            │
            ▼
  git commit + push (github-actions[bot])  ──►  GitHub Pages serves /data/dashboard/*
            │
            ▼
  make_dot_com-scenario-hook.yml (separate cron, daily 8:45 AM PT)
       └─►  POST to Make.com webhook  ──►  LinkedIn + Facebook publishing
```

---

## Source files (root of repo)

| File | Role |
|---|---|
| `config.py` | Tiny constants: `BASE_URL`, `DATASET_ID`, unused `DEFAULT_LIMIT` and `TIMEZONE`. |
| `full_exporter.py` | Streams the full dataset via `/exports/json`, gzips it, writes to `data/`. |
| `type_status_response_summary.py` | Parses latest export, builds per-type aggregates across 7 time windows, atomic-writes `summary_results_current.json` and an archive copy. Also fetches dataset metadata (`data_processed_at`, etc.) via the Opendatasoft catalog endpoint. |
| `LLM_inference.py` | Calls Gemini API for each timeframe (4h / 24h / 7d / 30d / 90d). Reads `GOOGLE_AI_STUDIO_API_KEY` from env. Has retry/backoff. |
| `generate_dashboard.py` | Builds five HTML dashboards with embedded Plotly charts + a status-breakdown table and the Past Days & Periods calendar. Loads LLM text from local files. Triggers PNG generation. Writes `archive.html`. |
| `build_archive_index.py` | Indexes `data/archive/` into `data/archive/index/` for the archive page and calendars. Incremental; backfills itself when no index exists. Tests in `tests/`. |
| `archive_ui.py` | The calendar (server-rendered, no JS) and the static archive page (`archive.html`, browser-rendered from archived files). |
| `site_common.py` | Banner link, PayPal support block and privacy note shared by every page. |
| `generate_charts.py` | Matplotlib bar chart + Pillow header/footer compositing → branded PNG. Loads DejaVuSans bundled with matplotlib for cross-platform fonts. |
| `generate_about_page.py` | Converts `README.md` → `data/dashboard/about.html`. |
| `trigger_make_webhook.py` | Posts a small JSON payload to a Make.com webhook URL using `MAKE_WEBHOOK_URL` + `MAKE_WEBHOOK_KEY` env vars. |
| `index.html` | Root redirect → `/data/dashboard/index_24hours.html`. |
| `support/index.html` | Redirect to PayPal support page. |
| `CNAME` | `hustlelongbeach.com` (GitHub Pages custom domain). |

## Workflows (`.github/workflows/`)

| Workflow | Trigger | Purpose |
|---|---|---|
| `Update_Data-Build_Dashboards.yml` | Cron 6×/day + manual | The end-to-end pipeline (export → parse → LLM → dashboards → about → commit). |
| `make_dot_com-scenario-hook.yml` | Cron daily 8:45 AM PT + manual | Fires the Make.com webhook to publish to LinkedIn / Facebook. |
| `test_llm_inference.yml` | Manual only | Re-runs `LLM_inference.py` against current summary JSON. |

**Cron schedules in `Update_Data-Build_Dashboards.yml` are set for PST (UTC−8).** During PDT (UTC−7, March–November) the actual fire time is one hour later than the comment suggests. The City publishes data at 3, 7, 11 AM/PM PT; current cron fires hit ~10 minutes after PST-equivalent windows, which means ~70 minutes after the 7 AM PDT publish. See the eval doc for fixes.

---

## Run locally

```bash
pip install -r requirements.txt

# 1. Pull fresh data
python3 full_exporter.py

# 2. Build summary JSON
python3 type_status_response_summary.py

# 3. (Requires GOOGLE_AI_STUDIO_API_KEY in env) generate LLM text
export GOOGLE_AI_STUDIO_API_KEY=...
python3 LLM_inference.py

# 4. Index the archive, then render dashboards + charts (+ archive.html)
python3 build_archive_index.py
python3 generate_dashboard.py
python3 generate_about_page.py
```

Open `data/dashboard/index_24hours.html` in a browser to preview.

Tests: `python -m pytest tests` (archive indexer). There is no linter config, pre-commit hook or formatter yet.

Preview the archive page over HTTP (it fetches files, so `file://` won't work): `python3 -m http.server` from the repo root, then open `/data/dashboard/archive.html`.

---

## Required secrets / env vars

| Name | Used by | Notes |
|---|---|---|
| `GOOGLE_AI_STUDIO_API_KEY` | `LLM_inference.py` | Gemini API key from Google AI Studio. |
| `MAKE_WEBHOOK_URL` | `trigger_make_webhook.py` | Make.com daily-post scenario URL. |
| `MAKE_WEBHOOK_KEY` | `trigger_make_webhook.py` | Make.com `x-make-apikey` header value. |
| `OPENAI_API_KEY` | `LLM_inference.py` (secondary cascade) | OpenAI API key. Cascades when Gemini fails. Per Decision Log D-05 (2026-04-30). |

Secrets are read from GitHub Actions repo secrets in CI.

---

## Conventions and gotchas

- **Only the scheduled publishing run calls the City's API.** It downloads the full dataset every four hours; that is the project's whole footprint on the City's servers. Checks (`pipeline-check.yml`), previews and development work use what is already here: `data/summary_results_current.json`, `data/archive/`, or the weekly raw snapshot on the `raw-snapshots-weekly` draft release (`gh release download`). Don't add a City download to any check, test or deploy step. A one-off audit that needs fresh City data downloads once, keeps the file out of the repo and deletes it afterwards.
- **All timestamps in stored data are UTC (Zulu).** Display logic in `generate_dashboard.py` and the LLM prompt converts to America/Los_Angeles for users.
- **`summary_results_current.json` is the single source of truth** consumed by both `LLM_inference.py` and `generate_dashboard.py`. Do not bypass it.
- **Status normalization** lives in `generate_dashboard.normalize_status()` — `Duplicate` is dropped from the dashboard tables. The summary JSON keeps duplicates.
- **Atomic writes** for the summary JSON are intentional (`write_json_atomically`). Don't replace with a plain `open(..., "w")` — concurrent reads from the dashboard generator could otherwise see a partial file.
- **`fetch-depth: 1`** (shallow checkout) is used by the pipeline. History was rewritten once (2026-10-07) to drop raw exports; any further history-rewriting operation must be planned carefully.
- **The repo IS the database.** Every 4 hours an archived JSON, an updated summary JSON, and (eventually) raw exports get committed. Pruning happens only on the working tree — git history retains everything forever. Plan accordingly before adding new artifact types.
- **Do not commit raw exports beyond the 7-day window** — the workflow's prune step deletes from disk only; if you stage them by accident they live in history forever.
- **Hardcoded brand colors** (`#0054ad` body, `#003c82` accent, white text) are duplicated across `generate_dashboard.py` and `generate_about_page.py`. Match them when editing either.
- **Archived files are an API.** `archive.html` and `build_archive_index.py` read `data/archive/YYYY/MM/summary_json_*.json` and `summary_<4_hour|24_hour|7_day|30_day|90_day>_*.txt` by name (UTC run-clock timestamps). Don't rename or move them; an archived view must keep its "ARCHIVE" notice and code-generated window statement.
- **The dashboard's "Privacy & Transparency" footer claims no cookies.** The PayPal embed loads PayPal-controlled assets; if you add analytics, telemetry, or third-party scripts, update that footer in both files.

---

## Don't do (without explicit approval)

- Don't `git filter-branch` / `git filter-repo` / `git push --force` to shrink history — the eval doc has a planned migration approach.
- Don't add server-side dependencies (Flask, FastAPI, databases). The whole point is the static + GHA model.
- Don't switch the LLM provider casually — model name, prompt, and output shape are coupled to the dashboard's status-box rendering.
- Don't rename `data/summary_results_current.json` or the `current_<period>_text_status.txt` filenames; they're consumed by both code and (likely) the Make.com scenario via direct URL.

---

## Reference docs

- Long Beach Open Data Portal: <https://longbeach.opendatasoft.com/>
- Dataset page: <https://longbeach.opendatasoft.com/explore/dataset/service-requests/>
- Opendatasoft (Huwise) Explore API v2.1: <https://help.opendatasoft.com/apis/ods-explore-v2/>
- Gemini API docs: <https://ai.google.dev/gemini-api/docs/>
- DeepWiki for this repo: <https://deepwiki.com/davidkarnowski/HustleYourCity>
- Live site: <https://hustlelongbeach.com>
