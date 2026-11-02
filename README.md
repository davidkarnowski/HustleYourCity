![Hustle Long Beach Banner](https://github.com/davidkarnowski/HustleYourCity/blob/main/docs/Hustle_Long_Beach_Banner.png)
# HustleYourCity (Long Beach)

## Overview
**Hustle Long Beach** is a civic accountability project designed to empower citizens by providing transparent, data-driven insights into the responsiveness of city services. The project leverages open government data from the **City of Long Beach, California**, to calculate average response times, total service calls, and departmental workloads.

This initiative aims to make service performance data accessible and meaningful for residents, journalists, and policymakers alike — encouraging constructive dialogue and efficient public resource management.

---

## Project Mission
This project exists to provide **citizens of Long Beach** with a clear and quantitative view of how their local government responds to requests for city services. While the city already offers open data through its [Long Beach Open Data Portal](https://longbeach.opendatasoft.com/), much of that information is presented in tables and GIS-style maps that are difficult for the average resident to interpret.

By automating the collection and analysis of these datasets, *Hustle Long Beach* transforms raw data into actionable insights — helping citizens understand where services excel and where improvements may be needed.

---

## Hustle Long Beach Dashboards

Explore the latest city service response time dashboards by time period (updated every four hours):

- [4-Hour Dashboard](https://HustleLongBeach.com/data/dashboard/index_4hours.html)  
- [24-Hour Dashboard](https://HustleLongBeach.com/data/dashboard/index_24hours.html)  
- [7-Day Dashboard](https://HustleLongBeach.com/data/dashboard/index_7days.html)  
- [30-Day Dashboard](https://HustleLongBeach.com/data/dashboard/index_30days.html)  
- [90-Day Dashboard](https://HustleLongBeach.com/data/dashboard/index_90days.html)
- [Archive: past days and periods](https://HustleLongBeach.com/data/dashboard/archive.html)

Every dashboard ends with a **Past Days & Periods** calendar, and the **Archive** button opens the full archive (details in the next section).

---

## Archive of Past Days and Periods

Every four-hour update is kept, so you can look back at what the dashboards showed on any past day.

- **Pick a day** on the calendar at the bottom of any dashboard, or open the [archive page](https://HustleLongBeach.com/data/dashboard/archive.html) and move between months.
- **Pick a window:** 4 Hours, 1 Day, 7 Days, 30 Days or 90 Days. A window is the stretch of time *ending* at the chosen update, so "7 Days" on October 15 shows the week that ended on October 15. The calendar shades the days the window covers.
- **Pick an update time:** each day usually has six updates. The last update of the day is shown by default; the buttons under the calendar select the others.
- **Share a view:** the address bar holds the day, window and update time, so a link reopens the same view.

**Every archived view is labelled as archived.** A yellow **ARCHIVE** notice sits at the top, and a window statement gives the window's start and end in Pacific time (PST/PDT), when the City last published its data, and when this site downloaded it. Titles and chart headings name the window, for example "7 Days ending Thursday, October 15, 2026 (Archived)".

**Archived numbers are shown as they were published.** Each view is rebuilt from the summary file and AI-written text saved by that update. Cases the City opened, closed or edited afterwards are not reflected, so an archived count or average can differ from what today's City data would give for the same window. The written summary is the AI model's text from that time, unedited; if the AI service was down at the time, the page says that an earlier summary was shown instead.

**Coverage:** response-time numbers are archived from October 16, 2025 and written summaries from late November 2025. The earliest updates did not record their exact download time, so those views say the time is approximate.

**How it works:** the archive is a single static page. Your browser loads a small index of past updates (`data/archive/index/`) and the saved files for the day you pick, then draws the same chart and table as the live dashboards. Nothing extra is generated per day, so the archive adds only a few kilobytes per update to the repository. Like the live charts, it needs JavaScript.

---

## Data Source
- **Dataset Name:** Go Long Beach Service Requests  
- **Source:** [Long Beach Open Data Portal](https://longbeach.opendatasoft.com/api/explore/v2.1/console)  
- **API Platform:** Huwise (formerly Opendatasoft)  
- **Update Frequency:** Every 4 hours  
- **Timezone:** America/Los_Angeles (PST/PDT)  

**City of Long Beach's Published Data Update Schedule:**  
- 3:00 AM  
- 7:00 AM  
- 11:00 AM  
- 3:00 PM  
- 7:00 PM  
- 11:00 PM  

---

## Core Python Scripts

### `full_exporter.py`
Downloads the complete dataset from the Long Beach open data API using the JSON export endpoint.  
Each export is saved as a timestamped file in the `data/` directory (e.g. `service_requests_full_20251016_070000.json`) for the duration of the run. Raw exports are not committed; see [Data Retention](#hosting-storage-and-data-retention).

**Functions:**
- Fetch full dataset via the `exports/json` API.
- Log all download attempts and file information.
- Save data atomically to prevent corruption.
  
---
### `type_status_response_summary.py`
Parses the exported dataset to compute service request summaries, including:
- Total counts per case type
- Status breakdowns (Closed, In Progress, New, etc.)
- Average response times (from creation to closure)
- Aggregated time windows: **All-Time**, **90 Days**, **60 Days**, **30 Days**, **7 Days**, **1 Day**, and **4 Hours**
- Each summary is saved as a timestamped JSON file (e.g. `summary_stats_20251016_070000.json`)

---
### `LLM_inference.py`
Generates natural language data summaries using Large Language Model chat completion with the JSON data summary used for user input. A specific system prompt is provided to the model to instruct to act like a civic-minded data evaluator and provide viewers with descriptions of the data that is contained in our parsed summary:
- Uses Google Gemini, with OpenAI as the fallback; if neither answers, the most recent archived summary is shown with a notice
- A base system prompt is combined with specific time-frame adenums to create prompts that focus on the five HLB data time-frames
- The HLB-parsed JSON data summary is provided as the user prompt
- Natural language data summaries are produced with every city data update and for every data time frame
  
---
### `generate_dashboard.py`
Generates HTML-based dashboards for each of the five data time periods included in the parsed JSON data summary. The HTML dashboard pages are hosted on GitHub pages and contain:
- Latest LLM-infered natural language data summary
- Interactive Plotly charts embeded in the page
- Table of service call counts and statuses
- A date-time stamp for when the data was collected for display
- Support link to a PayPal payment page (to support development and maintenance)
- GitHub project reference link (to this repo page)
- A **Past Days & Periods** calendar linking each archived day to the archive page
- The archive page itself (`data/dashboard/archive.html`), written from the shared styles in `archive_ui.py` and `site_common.py`

---
### `build_archive_index.py`
Indexes the archive after each update: it pairs every archived summary file with the AI-written texts from the same run and writes one index file per month (`data/archive/index/YYYY-MM.json`, keyed by Pacific date) plus `months.json`, which drives the calendars. It only rewrites files that changed, and on its first run it indexes the whole archive.

---
### `generate_charts.py`
Called as an external module during runtime and generates PNG images of charts which include:
- Header artwork of the "Hustle Long Beach!" project logo
- A bargraph reprsenting the current time-period's average response time data
- The date-time stamp of when the data was collected
- Charts are saved under `data/charts/` and are available via the GitHub Pages links for reference and sharing

---

## GitHub Actions Automation

The project is designed to run automatically in the cloud using **GitHub Actions** — no full VM or paid hosting required.

**Workflow:**
- Triggered every 4 hours, approximately ten minutes after each dataset update by the City of Long Beach (Pacific Time)
- Runs the exporter, parser, LLM inference routine, archive indexer and dashboard and chart generators
- Commits each summary, chart and dashboard to the repository for historical tracking (raw exports are not committed)

**Example GitHub Actions Schedule (UTC):**
```yaml
on:
  schedule:
    # Los Angeles times converted to UTC (LA is UTC−7 during DST)
    - cron: "10 14 * * *"   # 7:10 AM LA (14:10 UTC)
    - cron: "10 18 * * *"   # 11:10 AM LA (18:10 UTC)
    - cron: "10 22 * * *"   # 3:10 PM LA (22:10 UTC)
    - cron: "10 2 * * *"    # 7:10 PM LA (02:10 UTC next day)
    - cron: "10 6 * * *"    # 11:10 PM LA (06:10 UTC next day)
    - cron: "10 10 * * *"   # 3:10 AM LA (10:10 UTC)
```

---

## Running Locally

### Requirements

Install dependencies:
```bash
pip install -r requirements.txt
```

Run full export:
```bash
python3 full_exporter.py
```

Parse dataset and generate summaries:
```bash
python3 type_status_response_summary.py
```

Outputs will appear in the `data/` folder.

---

## Data Types and Categories

### Common Case Types
- Dumped Items  
- Graffiti  
- Tree Maintenance  
- Street Repair  
- Light  
- Sidewalk Repair  
- Dead Animal Pickup  
- Park Maintenance  
- Abandoned Shopping Cart  
- Animal Services  
- Vegetation  
- Trash & Debris  
- Traffic Signal  
- And more…

### Common Status Values
- Closed  
- In Progress  
- New  
- Cancelled  
- Closed Referred  
- Duplicate  

---

## Data Usage and Limitations

The project does not alter, filter, or modify the official Long Beach dataset. It performs read-only operations to calculate and display performance metrics.

While the calculations are accurate to the timestamps and data provided, users should note:
- City workers may close cases under different internal conditions.  
- Some records may not have complete timestamps.  
- Response times are approximations based on public data.  

---
## The Heart of LLM-Powered Natural Language Data Summaries

### How the summaries are written

The pipeline sends each time window's numbers (the summary JSON) to a large language model with a fixed system prompt and asks for a short, factual, plain-language update for Long Beach residents. The model is told that the project is independent of the City, to back every statement with the data, to express long response times in days or weeks and short ones in minutes, to encourage residents to report issues through the Go Long Beach app, and to end with the time the data was downloaded and when the City published it.

The prompt asks for plain text only (no emoji, markdown or special characters). That rule dates from when the summaries were also posted to social media, and it is kept because the dashboards show the text as written.

The prompt in use lives in [`llm/prompts.py`](llm/prompts.py), with a readable copy in [`docs/System_Prompt_Instructions_for_LLM-Powered_Natural_Language_Data_Summaries.md`](docs/System_Prompt_Instructions_for_LLM-Powered_Natural_Language_Data_Summaries.md). Google Gemini writes the summaries, with OpenAI as the fallback; if neither answers, the site shows the most recent archived summary and says so.

---

## Hosting, Storage and Data Retention

| Data | Where it lives | How long |
|---|---|---|
| Summaries (`data/archive/`, `data/summary_results_current.json`), LLM status text, dashboards and charts | Committed to this repository on every run | Full history, kept indefinitely |
| Archive index (`data/archive/index/`) | Rewritten when an update adds a run (a few KB) | Rebuilt from the archive, kept with it |
| Raw City exports (`service_requests_full_*.json.gz`) | Never committed. One export per ISO week is saved as an asset on a draft release (visible to maintainers only) | 12 weeks, then pruned automatically |

Every run downloads the City's **complete** dataset (every service request back to 2020), so the newest export always contains every record. The weekly copies guard against the source data being edited or withdrawn; they are not needed to rebuild the summaries.

Keeping full exports (about 11 MB each, six a day) out of git keeps the repository practical to clone and keeps the automated runs fast. The weekly retention lives in `.github/scripts/snapshot_raw_export.sh`.

---

## Social Media

Until October 2026, a daily summary and chart were posted automatically to the project's Facebook and LinkedIn pages through a Make.com scenario, started by a GitHub Actions webhook. That daily posting has been retired, and the project no longer uses Make.com. The dashboards and the archive are the project's home; the social pages now get occasional posts, such as a link to a new blog post, written by hand.

---

## Civic Impact
This project is built for **citizen accountability and transparency**.  
By providing simple, quantitative data on city responsiveness, we hope to:
- Empower citizens to understand how their city serves them.  
- Encourage resource prioritization where service lags occur.  
- Recognize departments and staff who perform exceptionally well.  

---

## Support Hustle Long Beach Development
If you want to support the continued development and maintenance of this project, you can send an amount of your choosing to our PayPal account. You pick how much support to provide. No PayPal account required.
[Support Hustle Long Beach! via PayPal - Click Here](https://www.paypal.com/ncp/payment/JYJDUKNCD4324)

---

HustleYourCity has been analyzed by DeepWiki and the documentation is avaiable for further reference:
[![Ask DeepWiki](https://deepwiki.com/badge.svg)](https://deepwiki.com/davidkarnowski/HustleYourCity)

---

## License

This project uses third-party open source libraries:

- plotly (MIT License) — https://github.com/plotly/plotly.py
- requests (Apache 2.0 License) — https://github.com/psf/requests
- pytz (MIT License) — https://github.com/stub42/pytz
- matplotlib (BSD-compatible / PSF-based License) — https://github.com/matplotlib/matplotlib


All other dependencies are standard Python libraries distributed under the
Python Software Foundation License.
