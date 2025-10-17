import json
import plotly.graph_objects as go
from pathlib import Path

# -------------------- CONFIGURATION --------------------
DATA_URL = "https://longbeach.opendatasoft.com/explore/dataset/service-requests/information/"
PERIODS = {
    "24hours": "Last 1 Days",
    "7days": "Last 7 Days",
    "30days": "Last 30 Days",
    "90days": "Last 90 Days",
}
OUTPUT_DIR = Path("data/dashboard")
BANNER_PATH = "Hustle_Long_Beach_Banner.png"
GITHUB_LINK = "https://github.com/davidkarnowski/HustleYourCity"

# -------------------------------------------------------

def normalize_status(status: str) -> str:
    """Normalize status names (combine closed variants, skip duplicates)."""
    s = status.strip().lower()
    if "duplicate" in s:
        return None
    if "closed" in s:
        return "Closed"
    if "in progress" in s:
        return "In Progress"
    if "open" in s:
        return "Open"
    return status.title()

def build_dashboard(period_label: str, dataset: dict):
    """Generate a dashboard HTML file for a specific time period."""

    period_name = PERIODS[period_label]
    period_data = dataset.get(period_name, {}).get("types", {})

    # -------------------- DATA AGGREGATION --------------------
    avg_response_list = []
    table_data = {}

    for case_type, values in period_data.items():
        if not isinstance(values, dict):
            continue
        if "duplicate" in case_type.lower():
            continue

        avg_hours = values.get("avg_response_hours")
        if avg_hours is not None:
            avg_response_list.append((case_type, avg_hours))

        statuses = values.get("statuses") or values.get("status_counts") or {}
        if isinstance(statuses, list):
            normalized = {}
            for entry in statuses:
                if isinstance(entry, dict):
                    for k, v in entry.items():
                        norm = normalize_status(k)
                        if norm:
                            normalized[norm] = normalized.get(norm, 0) + int(v)
            statuses = normalized
        elif isinstance(statuses, dict):
            normalized = {}
            for k, v in statuses.items():
                norm = normalize_status(k)
                if norm:
                    normalized[norm] = normalized.get(norm, 0) + int(v)
            statuses = normalized

        table_data[case_type] = statuses

    # -------------------- SORTING --------------------
    avg_response_list.sort(key=lambda x: x[1] if x[1] is not None else 0, reverse=True)
    types_sorted = [x[0] for x in avg_response_list]
    avg_sorted = [x[1] for x in avg_response_list]

    # -------------------- PLOT 1: AVERAGE RESPONSE --------------------
    fig1 = go.Figure(
        data=[
            go.Bar(
                y=list(types_sorted),
                x=list(avg_sorted),
                orientation="h",
                marker_color="#ffffff",
            )
        ]
    )
    fig1.update_layout(
        title=f"Average Response Time (Hours) — {period_label.replace('days', ' Days').replace('hours', ' Hours').title()} View",
        xaxis_title="Hours",
        yaxis_title="Service Type",
        template="plotly_dark",
        plot_bgcolor="#0054ad",
        paper_bgcolor="#0054ad",
        font=dict(color="white"),
        margin=dict(l=180, r=50, t=80, b=50),
        height=700,
    )

    # -------------------- TABLE: STATUS BREAKDOWN --------------------
    all_statuses = sorted(
        {s for statuses in table_data.values() for s in statuses.keys()}
    )

    service_types = []
    column_values = {s: [] for s in all_statuses}
    total_col = []

    for case_type, statuses in table_data.items():
        service_types.append(case_type)
        total = 0
        for s in all_statuses:
            val = statuses.get(s, 0)
            column_values[s].append(val)
            total += val
        total_col.append(total)

    header_vals = ["Service Type"] + all_statuses + ["Total"]
    cell_vals = [service_types] + [column_values[s] for s in all_statuses] + [total_col]

    fig2 = go.Figure(
        data=[
            go.Table(
                header=dict(
                    values=header_vals,
                    fill_color="#003c82",
                    font=dict(color="white", size=13),
                    align="left",
                ),
                cells=dict(
                    values=cell_vals,
                    fill_color=[["#004b9b" if i % 2 == 0 else "#0054ad" for i in range(len(service_types))]],
                    font=dict(color="white", size=12),
                    align="left",
                ),
            )
        ]
    )
    fig2.update_layout(
        title=f"Service Call Status Breakdown — {period_label.replace('days', ' Days').replace('hours', ' Hours').title()}",
        plot_bgcolor="#0054ad",
        paper_bgcolor="#0054ad",
        font=dict(color="white"),
        margin=dict(l=30, r=30, t=40, b=10),  # Reduced extra vertical space
        height=700 + len(service_types) * 10,
    )

    # -------------------- NAVIGATION BUTTONS --------------------
    nav_html = """
    <div class="nav-buttons">
      <a href="index_24hours.html" class="nav-btn">24 Hours</a>
      <a href="index_7days.html" class="nav-btn">7 Days</a>
      <a href="index_30days.html" class="nav-btn">30 Days</a>
      <a href="index_90days.html" class="nav-btn">90 Days</a>
    </div>
    """

    # -------------------- HTML PAGE --------------------
    html_path = OUTPUT_DIR / f"index_{period_label}.html"
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    with open(html_path, "w") as f:
        f.write(f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Hustle Long Beach Dashboard — {period_label.replace('days', ' Days').replace('hours', ' Hours').title()} View</title>
  <style>
    body {{
      background-color: #0054ad;
      color: white;
      font-family: 'Segoe UI', Arial, sans-serif;
      margin: 0;
      padding: 20px;
    }}
    h1 {{
      text-align: center;
      color: white;
      margin-top: 10px;
      margin-bottom: 20px;
    }}
    a {{
      color: #ffffff;
      text-decoration: none;
    }}
    .banner {{
      width: 100%;
      max-width: 900px;
      display: block;
      margin: 0 auto 10px auto;
      border-radius: 12px;
      box-shadow: 0 0 15px rgba(0,0,0,0.4);
    }}
    .nav-buttons {{
      display: flex;
      justify-content: center;
      gap: 15px;
      margin: 20px 0 30px 0;
    }}
    .nav-btn {{
      background-color: white;
      color: #0054ad;
      padding: 10px 20px;
      border-radius: 6px;
      font-weight: 600;
      transition: 0.3s;
    }}
    .nav-btn:hover {{
      background-color: #d9eaff;
    }}
    .source-note {{
      margin: 15px 0;
      font-size: 0.9em;
      text-align: center;
    }}
    .footer {{
      margin-top: 20px;  /* reduced space above footer */
      font-size: 0.9em;
      color: #e0e0e0;
      border-top: 1px solid #ffffff44;
      padding-top: 10px;
      text-align: center;
    }}
  </style>
</head>
<body>
  <img src="{BANNER_PATH}" alt="Hustle Long Beach Banner" class="banner">
  <h1>City Service Dashboard — {period_label.replace('days', ' Days').replace('hours', ' Hours').title()} View</h1>
  {nav_html}
  <div class="source-note">
    Data Source: <a href="{DATA_URL}" target="_blank">Go Long Beach Service Requests (Open Data Portal)</a>
  </div>
""")
        f.write(fig1.to_html(full_html=False, include_plotlyjs='cdn'))
        f.write("<br>\n")
        f.write(fig2.to_html(full_html=False, include_plotlyjs=False))
        f.write(f"""
  <div class="footer">
    <p>Disclaimer: This dashboard is generated automatically from Long Beach’s public service request dataset via the Go Long Beach app. Accuracy depends on city data quality and parsing reliability.</p>
    <p>Project Source: <a href="{GITHUB_LINK}" target="_blank">HustleYourCity on GitHub</a></p>
  </div>
</body>
</html>
""")

    print(f"✅ Dashboard generated: {html_path.resolve()}")

def main():
    """Generate multiple time-period dashboards."""
    data_path = Path("data/summary_results_current.json")
    if not data_path.exists():
        raise FileNotFoundError(f"File not found: {data_path}")

    with open(data_path, "r") as f:
        dataset = json.load(f)

    for period in PERIODS.keys():
        build_dashboard(period, dataset)

if __name__ == "__main__":
    main()
