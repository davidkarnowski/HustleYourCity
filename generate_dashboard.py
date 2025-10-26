import json
import plotly.graph_objects as go
from pathlib import Path
from datetime import datetime
import pytz
import requests
from generate_charts import create_and_enhance_chart  # NEW import

# -------------------- CONFIGURATION --------------------
DATA_URL = "https://longbeach.opendatasoft.com/explore/dataset/service-requests/information/"
PERIODS = {
    "4hours": "Last 4 Hours",
    "24hours": "Last 1 Days",
    "7days": "Last 7 Days",
    "30days": "Last 30 Days",
    "90days": "Last 90 Days",
}
OUTPUT_DIR = Path("data/dashboard")
CHART_DIR = Path("data/charts")  # for saving PNG charts
BANNER_PATH = "Hustle_Long_Beach_Banner.png"
GITHUB_LINK = "https://github.com/davidkarnowski/HustleYourCity"
STATUS_TEXT_URL = (
    "https://raw.githubusercontent.com/davidkarnowski/HustleYourCity/main/data/current_text_status.txt"
)
LOGO_PATH = Path("data/art/chart_logo.png")  # static branding logo
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


def format_timestamp(timestamp_utc_str: str) -> str:
    """Convert UTC timestamp to readable Pacific time."""
    if not timestamp_utc_str or timestamp_utc_str == "Unknown":
        return "Unknown time"
    try:
        utc_time = datetime.fromisoformat(timestamp_utc_str.replace("Z", "+00:00"))
        local_tz = pytz.timezone("America/Los_Angeles")
        local_time = utc_time.astimezone(local_tz)
        return local_time.strftime("%B %d, %Y at %I:%M:%S %p %Z")
    except Exception:
        return timestamp_utc_str


def fetch_current_status_text() -> str:
    """Fetch the latest status update text from GitHub."""
    try:
        response = requests.get(STATUS_TEXT_URL, timeout=10)
        if response.status_code == 200:
            text = response.text.strip()
            if len(text) > 2000:
                text = text[:2000] + "..."
            return text
        else:
            return f"(Unable to load status text — HTTP {response.status_code})"
    except Exception as e:
        return f"(Error loading status text: {e})"


def build_dashboard(period_label: str, dataset: dict, downloaded_at_str: str):
    """Generate dashboard HTML + PNG chart for a specific period."""
    period_name = PERIODS[period_label]
    period_data = dataset.get(period_name, {}).get("types", {})

    current_status_text = fetch_current_status_text()

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
    avg_response_list = [x for x in avg_response_list if x[1] is not None]
    avg_response_list.sort(key=lambda x: x[1], reverse=True)
    types_sorted = [x[0] for x in avg_response_list]
    avg_sorted = [x[1] for x in avg_response_list]

    # -------------------- PLOTLY CHART (HTML) --------------------
    if types_sorted:
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
            title=f"Average Response Time (Hours) — {PERIODS[period_label]} View",
            xaxis_title="Hours",
            yaxis_title="Service Type",
            template="plotly_dark",
            plot_bgcolor="#0054ad",
            paper_bgcolor="#0054ad",
            font=dict(color="white"),
            margin=dict(l=180, r=50, t=80, b=50),
            height=max(400, 30 * len(types_sorted) + 200),
        )
        plot1_html = fig1.to_html(full_html=False, include_plotlyjs="cdn")

        # -------------------- STATIC PNG EXPORT (Matplotlib + Pillow) --------------------
        CHART_DIR.mkdir(parents=True, exist_ok=True)
        png_path = CHART_DIR / f"average_response_{period_label}.png"

        try:
            create_and_enhance_chart(
                png_path=png_path,
                service_types=types_sorted,
                avg_values=avg_sorted,
                title=f"Average Response Time — {PERIODS[period_label]}",
                downloaded_at=downloaded_at_str,
                logo_path=LOGO_PATH,
            )
            print(f"✅ PNG chart created and enhanced: {png_path.resolve()}")
        except Exception as e:
            print(f"⚠️ Could not generate PNG for {period_label}: {e}")

    else:
        plot1_html = "<p style='text-align:center;font-size:1.2em;margin:40px 0;'>No average response time data for this period.</p>"

    # -------------------- TABLE (Plotly) --------------------
    table_data = {k: v for k, v in table_data.items() if v}
    if table_data:
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
                        fill_color=[
                            ["#004b9b" if i % 2 == 0 else "#0054ad" for i in range(len(service_types))]
                        ],
                        font=dict(color="white", size=12),
                        align="left",
                    ),
                )
            ]
        )
        fig2.update_layout(
            title=f"Service Call Status Breakdown — {PERIODS[period_label]}",
            plot_bgcolor="#0054ad",
            paper_bgcolor="#0054ad",
            font=dict(color="white"),
            margin=dict(l=30, r=30, t=40, b=10),
            height=max(400, len(service_types) * 35 + 150),
        )
        plot2_html = fig2.to_html(full_html=False, include_plotlyjs=False)
    else:
        plot2_html = f"<p style='text-align:center;font-size:1.2em;margin:40px 0;'>No service request data found for this period ({period_name}).</p>"

    # -------------------- NAVIGATION BUTTONS --------------------
    nav_html_parts = ['<div class="nav-buttons">']
    for p_label, p_name in PERIODS.items():
        btn_text = p_name.replace("Last ", "")
        if p_label == period_label:
            nav_html_parts.append(
                f'<a href="index_{p_label}.html" class="nav-btn nav-btn-active">{btn_text}</a>'
            )
        else:
            nav_html_parts.append(
                f'<a href="index_{p_label}.html" class="nav-btn">{btn_text}</a>'
            )
    nav_html_parts.append("</div>")
    nav_html = "\n".join(nav_html_parts)

    # -------------------- HTML PAGE --------------------
    html_path = OUTPUT_DIR / f"index_{period_label}.html"
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    with open(html_path, "w") as f:
        f.write(f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Hustle Long Beach Dashboard — {PERIODS[period_label]} View</title>
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
      margin-bottom: 10px;
    }}
    .status-box {{
      background-color: #003c82;
      border-left: 5px solid #ffffff;
      padding: 15px 20px;
      margin: 20px auto;
      max-width: 850px;
      border-radius: 10px;
      box-shadow: 0 0 10px rgba(0,0,0,0.3);
      font-size: 1.05em;
      line-height: 1.5em;
      white-space: pre-wrap;
    }}
    .status-title {{
      font-weight: bold;
      font-size: 1.2em;
      margin-bottom: 8px;
      text-align: center;
      text-transform: uppercase;
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
      flex-wrap: wrap;
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
      border: 2px solid white;
    }}
    .nav-btn:hover {{
      background-color: #d9eaff;
    }}
    .nav-btn-active {{
      background-color: #003c82;
      color: white;
      font-weight: bold;
    }}
    .source-note {{
      margin: 15px 0;
      font-size: 0.9em;
      text-align: center;
    }}
    .footer {{
      margin-top: 20px;
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
  <h1>City Service Dashboard — {PERIODS[period_label]} View</h1>

  <div class="status-box">
    <div class="status-title">Current Status Update</div>
    <div class="status-text">{current_status_text}</div>
  </div>

  {nav_html}
  <div class="source-note">
    Data Source: <a href="{DATA_URL}" target="_blank">Go Long Beach Service Requests (Open Data Portal)</a>
    <br>
    <strong>Data as of: {downloaded_at_str}</strong>
  </div>
""")
        f.write(plot1_html)
        f.write("<br>\n")
        f.write(plot2_html)
        f.write("""
  <div style="text-align:center; margin:40px auto 20px auto; max-width:800px;">
    <h2 style="font-size:1.1em; font-weight:600; margin-bottom:0.75rem;">
      Support the continued development and maintenance of the Hustle Long Beach! project.<br>
      Any amount is appreciated and no PayPal account is required.
    </h2>
    <div>
      <style>.pp-JYJDUKNCD4324{text-align:center;border:none;border-radius:0.25rem;min-width:11.625rem;padding:0 2rem;height:2.625rem;font-weight:bold;background-color:#FFD140;color:#000000;font-family:"Helvetica Neue",Arial,sans-serif;font-size:1rem;line-height:1.25rem;cursor:pointer;}</style>
      <form action="https://www.paypal.com/ncp/payment/JYJDUKNCD4324" method="post" target="_blank" style="display:inline-grid;justify-items:center;align-content:start;gap:0.5rem;">
        <input class="pp-JYJDUKNCD4324" type="submit" value="Buy Now" />
        <img src="https://www.paypalobjects.com/images/Debit_Credit.svg" alt="cards" />
        <section style="font-size:0.75rem;">
          Powered by <img src="https://www.paypalobjects.com/paypal-ui/logos/svg/paypal-wordmark-color.svg" alt="paypal" style="height:0.875rem;vertical-align:middle;"/>
        </section>
      </form>
    </div>
  </div>
  <div class="footer">
    <p>Disclaimer: This dashboard is generated automatically from Long Beach’s public service request dataset via the Go Long Beach app. Accuracy depends on city data quality and parsing reliability.</p>
    <p>Project Source: <a href="{GITHUB_LINK}" target="_blank">HustleYourCity on GitHub</a></p>
  </div>
</body>
</html>
""")

    print(f"✅ Dashboard generated: {html_path.resolve()}")


def main():
    """Generate dashboards and PNG charts for all time periods."""
    data_path = Path("data/summary_results_current.json")
    if not data_path.exists():
        data_path = Path("data.json")
        if not data_path.exists():
            raise FileNotFoundError("Could not find data file at data/summary_results_current.json or data.json")

    print(f"Loading data from: {data_path}")
    with open(data_path, "r") as f:
        dataset = json.load(f)

    raw_timestamp = dataset.get("downloaded_at", "Unknown")
    formatted_timestamp = format_timestamp(raw_timestamp)

    for period in PERIODS.keys():
        if PERIODS[period] not in dataset:
            print(f"⚠️ Warning: Period '{PERIODS[period]}' not found in JSON data. Skipping.")
            continue
        build_dashboard(period, dataset, formatted_timestamp)


if __name__ == "__main__":
    main()
