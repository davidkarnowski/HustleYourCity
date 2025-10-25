import json
import plotly.graph_objects as go
from pathlib import Path
from datetime import datetime
import pytz
import requests
import matplotlib.pyplot as plt  # NEW: for static PNG export

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
    """Convert UTC timestamp string to readable, localized format."""
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
    """Fetch the latest 'Current Status Update' text file from GitHub."""
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
    """Generate a dashboard HTML file and PNG chart for a specific time period."""

    period_name = PERIODS[period_label]
    period_data = dataset.get(period_name, {}).get("types", {})

    current_status_text = fetch_current_status_text()

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

    # -------------------- PLOT 1: AVERAGE RESPONSE --------------------
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

        # --- Matplotlib PNG Export (dark-styled) ---
        CHART_DIR.mkdir(parents=True, exist_ok=True)
        png_path = CHART_DIR / f"average_response_{period_label}.png"

        try:
            plt.figure(figsize=(8, 0.4 * len(types_sorted) + 2))
            plt.barh(types_sorted, avg_sorted, color="#ffffff")

            # Apply dark theme to match Plotly_dark
            ax = plt.gca()
            ax.set_facecolor("#0054ad")          # Plot background
            plt.gcf().set_facecolor("#0054ad")   # Figure background
            ax.tick_params(colors="white", labelsize=10)
            for spine in ax.spines.values():
                spine.set_color("white")

            # Labels and title
            plt.xlabel("Average Response Time (Hours)", color="white", fontsize=11)
            plt.ylabel("Service Type", color="white", fontsize=11)
            plt.title(f"Average Response Time — {PERIODS[period_label]}", color="white", fontsize=13, pad=15)

            plt.gca().invert_yaxis()  # keep longest times at top
            plt.tight_layout()
            plt.savefig(png_path, facecolor="#0054ad", bbox_inches="tight", dpi=150)
            plt.close()

            print(f"✅ PNG chart saved via Matplotlib: {png_path.resolve()}")

        except Exception as e:
            print(f"⚠️  Could not save PNG for {period_label} chart: {e}")
        # ----------------------------------------------------------
    else:
        plot1_html = "<p style='text-align: center; font-size: 1.2em; margin: 40px 0;'>No average response time data for this period.</p>"

    # -------------------- TABLE: STATUS BREAKDOWN --------------------
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
        cell_vals = [service_types] + [
            column_values[s] for s in all_statuses
        ] + [total_col]

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
                            [
                                "#004b9b" if i % 2 == 0 else "#0054ad"
                                for i in range(len(service_types))
                            ]
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
        plot2_html = f"<p style='text-align: center; font-size: 1.2em; margin: 40px 0;'>No service request data found for this period ({period_name}).</p>"

    # -------------------- SAVE HTML --------------------
    html_path = OUTPUT_DIR / f"index_{period_label}.html"
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with open(html_path, "w") as f:
        f.write(f"<html><body><h1>{PERIODS[period_label]}</h1>{plot1_html}{plot2_html}</body></html>")

    print(f"✅ Dashboard generated: {html_path.resolve()}")


def main():
    """Generate dashboards and PNGs for all time periods."""
    data_path = Path("data/summary_results_current.json")
    if not data_path.exists():
        data_path = Path("data.json")
        if not data_path.exists():
            raise FileNotFoundError(
                f"Could not find data file at {data_path} or data/summary_results_current.json"
            )

    print(f"Loading data from: {data_path}")
    with open(data_path, "r") as f:
        dataset = json.load(f)

    raw_timestamp = dataset.get("downloaded_at", "Unknown")
    formatted_timestamp = format_timestamp(raw_timestamp)

    for period in PERIODS.keys():
        if PERIODS[period] not in dataset:
            print(f"⚠️  Warning: Period '{PERIODS[period]}' not found in JSON data. Skipping.")
            continue
        build_dashboard(period, dataset, formatted_timestamp)


if __name__ == "__main__":
    main()
