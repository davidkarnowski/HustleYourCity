# HustleYourCity (Long Beach)

## Overview
**Hustle Long Beach** is a civic accountability project designed to empower citizens by providing transparent, data-driven insights into the responsiveness of city services. The project leverages open government data from the **City of Long Beach, California**, to calculate average response times, total service calls, and departmental workloads.

This initiative aims to make service performance data accessible and meaningful for residents, journalists, and policymakers alike — encouraging constructive dialogue and efficient public resource management.

---

## Project Mission
This project exists to provide **citizens of Long Beach** with a clear and quantitative view of how their local government responds to requests for city services. While the city already offers open data through its [Long Beach Open Data Portal](https://longbeach.opendatasoft.com/), much of that information is presented in tables and GIS-style maps that are difficult for the average resident to interpret.

By automating the collection and analysis of these datasets, *Hustle Long Beach* transforms raw data into actionable insights — helping citizens understand where services excel and where improvements may be needed.

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

Each summary is saved as a timestamped JSON file (e.g. `summary_stats_20251016_070000.json`) for future dashboard integration.

---

## GitHub Actions Automation

The project is designed to run automatically in the cloud using **GitHub Actions** — no full VM or paid hosting required.

**Workflow:**
- Triggered every 4 hours, approximately one minute after each dataset update (Pacific Time).
- Runs both the exporter and parser.
- Saves each dataset and summary to the repository for historical tracking.

**Example GitHub Actions Schedule (UTC):**
```yaml
on:
  schedule:
    - cron: '1 10,14,18,22,2,6 * * *'  # runs ~1 min after LB dataset update in Pacific time
```

---

## Running Locally

### Requirements
Python 3.9+ recommended.

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

## Future Goals
- Publish a public web dashboard to visualize key metrics.
- Enable filters by department, service type, and neighborhood.  
- Allow citizens to explore trends over time interactively.

---

## Civic Impact
This project is built for **citizen accountability and transparency**.  
By providing simple, quantitative data on city responsiveness, we hope to:
- Empower citizens to understand how their city serves them.  
- Encourage resource prioritization where service lags occur.  
- Recognize departments and staff who perform exceptionally well.  

---

## License
NaN
