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

- [4-Hour Dashboard](https://davidkarnowski.github.io/HustleYourCity/data/dashboard/index_4hours.html)  
- [24-Hour Dashboard](https://davidkarnowski.github.io/HustleYourCity/data/dashboard/index_24hours.html)  
- [7-Day Dashboard](https://davidkarnowski.github.io/HustleYourCity/data/dashboard/index_7days.html)  
- [30-Day Dashboard](https://davidkarnowski.github.io/HustleYourCity/data/dashboard/index_30days.html)  
- [90-Day Dashboard](https://davidkarnowski.github.io/HustleYourCity/data/dashboard/index_90days.html)

---

## Data Source
- **Dataset Name:** Go Long Beach Service Requests  
- **Source:** [Long Beach Open Data Portal](https://longbeach.opendatasoft.com/api/explore/v2.1/console)  
- **API Platform:** Huwise (formerly Opendatasoft)  
- **Update Frequency:** Every 4 hours  
- **Timezone:** America/Los_Angeles (PST/PDT)  

**Typical Update Schedule:**  
- 3:00 AM  
- 7:00 AM  
- 11:00 AM  
- 3:00 PM  
- 7:00 PM  
- 11:00 PM  

---

## Core Python Scripts

### 1. `full_exporter.py`
Downloads the complete dataset from the Long Beach open data API using the JSON export endpoint.  
Each export is saved as a timestamped file in the `data/` directory (e.g. `service_requests_full_20251016_070000.json`).

**Functions:**
- Fetch full dataset via the `exports/json` API.
- Log all download attempts and file information.
- Save data atomically to prevent corruption.

### 2. `type_status_response_summary.py`
Parses the exported dataset to compute service request summaries, including:
- Total counts per case type
- Status breakdowns (Closed, In Progress, New, etc.)
- Average response times (from creation to closure)
- Aggregated time windows: **All-Time**, **90 Days**, **60 Days**, **30 Days**, **7 Days**, **1 Day**, and **4 Hours**
- Each summary is saved as a timestamped JSON file (e.g. `summary_stats_20251016_070000.json`)

### 3. `generate_dashboards.py`
Generates HTML-based dashboards for each of the five data time periods included in the parsed JSON data summary. The HTML dashboard pages are hosted on GitHub pages and contain:
- Latest LLM-infered natural language data summary
- Interactive Plotly charts embeded in the page
- Table of service call counts and statuses
- A date-time stamp for when the data was collected for display
- Support link to a PayPal payment page (to support development and maintenance)
- GitHub project reference link (to this repo page)

### 4. `generate_charts.py`
Called as an external module during runtime and generates PNG images of charts which include:
- Header artwork of the "Hustle Long Beach!" project logo
- A bargraph reprsenting the current time-period's average response time data
- The date-time stamp of when the data was collected
- Charts are saved under ./Data/Charts and are available via the GitHub pages links for external refernce and inclusion in social media posts

---

## GitHub Actions Automation

The project is designed to run automatically in the cloud using **GitHub Actions** — no full VM or paid hosting required.

**Workflow:**
- Triggered every 4 hours, approximately ten minutes after each dataset update by the City of Long Beach (Pacific Time)
- Runs the exporter, parser and the dashboard and chart generators
- Saves each dataset and summary to the repository for historical tracking

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

## Hosting and Storage

Each export and summary is committed to the GitHub repository as historical reference.  
GitHub provides a **1 GB soft limit** for repositories and **2 GB hard limit** for overall storage; regular pruning or external storage may be added as the dataset grows.

---

## Automated AI-Powered Analsyis Publishing Using LLM Inference and Make.com Scenario
![Hustle Long Beach Make.com Scenario](https://github.com/davidkarnowski/HustleYourCity/blob/main/docs/Hustle_Long_Beach-Make_dot_com-Scenario_Workflow.png)

---

### Make.com Automated Workflow "Scenario" Description  
This scenario is designed to produce LLM completions based on structured data input parsed from the City of Long Beach, California’s open service call dataset. The scenario is initiated by a webhook request call sent from the project’s associated GitHub Actions workflow once every 24 hours.

The initial module following the Make.com webhook module is an HTTPS **“Get a File”** module, which retrieves the most recent parsed data from a public GitHub URL. The data file itself is a **JSON-formatted summary** produced by a parsing script that runs every four hours as a GitHub Action — matching the update frequency of the City of Long Beach dataset.

After the JSON file is downloaded, it is used as input to a **Cerebras.ai** module, where it is combined with a system prompt to produce a chat completion based on the structured data.

System Prompt Used for Data Analysis by Large Language Models:

>You are a third-party government accountability JSON interpreter for the HustleLongBeach community that evaluates city service response times. You are not officially part of Long Beach government and you do not represent any agency management so do not refer to the work as ours or done by “we”. You are ready to make sense of city service data from the Long Beach service call data via JSON. Evaluate the data and write a short social media update about the latest data update. We don't need all the data to be revealed and the post created should be short enough for a social media post. Let's make sure we talk about significant data changes in the past 24-hours and any case type that has significantly low or high response times (in hours). Make the data interpretable for the citizens of Long Beach. Hour counts over 72-hours should be expressed in days, weeks or months. Hour counts below 90 minutes should be measured in minutes. Remember that you are just trying to make sure the public knows about the latest response times, call totals and changes. In general, let's ignore data that is older than 90 days, but certainly report on our 1-day, 7-day and 30-day trends as the followers want recent and relevant reporting. Use facts and statistics to back up your post's language, always being factual about your response. Encourage followers to use the Go Long Beach service application to report issues to the city. Use straight-forward and simple language, nothing elaborate or flowery. 
>
>When writing the LinkedIn post, use only plain text that conforms to LinkedIn's Little Text Format:
>- Do not include any emojis or non-ASCII characters (avoid symbols like 🚨📱, smart quotes, or narrow spaces).
>- Use only straight quotes (" ") and apostrophes ('), and standard hyphens (-).
>- Replace all non-breaking spaces with normal spaces.
>- Do not include markdown, HTML, or Unicode styling.
>- Separate paragraphs with a single blank line.
>- Output only the final post text, no metadata, no labels, and no code block formatting.
>
>You very last line should always include the date-time stamp of the JSON ""downloaded_at"" field. This will let users know when this summary was produced. Because this value with be zulu(utc), convert it to Pacific Time. Use the format "This data summary was updated at <insert "downloaded_at" value>.


The model used by the Cerebras call is currently set to **GPT-OSS 120B**. The output of this inference is stored as an `LLM_Response` variable in the subsequent “tools” module, which then routes the response to three different outputs: **GitHub**, **Facebook Pages**, and **LinkedIn**.

#### GitHub LLM Response Update  
The routed GitHub flow contains two modules. The first makes an HTTPS request to the public project repository to retrieve the SHA hash value of the most recently updated `current_text_status.txt` file. The second performs an HTTPS PUT request to update that file with the latest `LLM_Response` variable.

#### Facebook Pages Status Publishing
The routed `LLM_Response` variable is also sent to a Make.com connector for **Facebook Pages**, publishing the latest inferred status update to the **Hustle Long Beach** community page.

#### LinkedIn Organization Stauts Publishing
The final route for the `LLM_Response` variable is a Make.com connector for **LinkedIn**, where the same inferred chat completion is published on the **Hustle Long Beach** organization page.

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

## License

This project uses third-party open source libraries:

- plotly (MIT License) — https://github.com/plotly/plotly.py
- requests (Apache 2.0 License) — https://github.com/psf/requests
- pytz (MIT License) — https://github.com/stub42/pytz
- matplotlib (BSD-compatible / PSF-based License) — https://github.com/matplotlib/matplotlib


All other dependencies are standard Python libraries distributed under the
Python Software Foundation License.
