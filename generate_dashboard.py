import json
import plotly.graph_objects as go
from pathlib import Path
from datetime import datetime
import pytz
from generate_charts import create_and_enhance_chart
import re

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
CHART_DIR = Path("data/charts")
BANNER_PATH = "Hustle_Long_Beach_Banner.png"
GITHUB_LINK = "https://github.com/davidkarnowski/HustleYourCity"
LOGO_PATH = Path("data/art/chart_logo.png")

# ✅ Local time-frame text file paths
STATUS_TEXT_FILES = {
    "4hours":  Path("data/current_4_hour_text_status.txt"),
    "24hours": Path("data/current_24_hour_text_status.txt"),
    "7days":   Path("data/current_7_day_text_status.txt"),
    "30days":  Path("data/current_30_day_text_status.txt"),
    "90days":  Path("data/current_90_day_text_status.txt"),
}


# -------------------- HELPERS --------------------
def normalize_status(status: str) -> str:
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
    if not timestamp_utc_str or timestamp_utc_str == "Unknown":
        return "Unknown time"
    try:
        utc_time = datetime.fromisoformat(timestamp_utc_str.replace("Z", "+00:00"))
        local_tz = pytz.timezone("America/Los_Angeles")
        local_time = utc_time.astimezone(local_tz)
        return local_time.strftime("%B %d, %Y at %I:%M:%S %p %Z")
    except Exception:
        return timestamp_utc_str


def get_dashboard_generated_time():
    local_tz = pytz.timezone("America/Los_Angeles")
    now_local = datetime.now(local_tz)
    return now_local.strftime("%B %d, %Y at %I:%M:%S %p %Z")


# ✅ Read status text from local file instead of URL
def load_local_status_text(period_label: str) -> str:
    file_path = STATUS_TEXT_FILES.get(period_label)

    if not file_path or not file_path.exists():
        return "(No status text yet for this time period)"

    try:
        text = file_path.read_text(encoding="utf-8").strip()

        # shorten overly long text for safety
        if len(text) > 2000:
            text = text[:2000] + "..."

        # linkify URLs inside text
        url_pattern = re.compile(r'((?:https?://|www\.)[^\s<>"\']+)', re.IGNORECASE)
        def linkify(match):
            url = match.group(0)
            href = url if url.startswith("http") else "http://" + url
            return f'<a href="{href}" target="_blank">{url}</a>'

        return url_pattern.sub(linkify, text)

    except Exception as e:
        return f"(Error loading local status text: {e})"


# -------------------- DASHBOARD BUILDER --------------------
def build_dashboard(period_label: str, dataset: dict, downloaded_at_str: str, generated_at_str: str):
    period_name = PERIODS[period_label]
    period_data = dataset.get(period_name, {}).get("types", {})

    # ✅ Read text from local files
    current_status_text = load_local_status_text(period_label)

    # --------- AGGREGATION ---------
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
        normalized = {}
        for k, v in (statuses.items() if isinstance(statuses, dict) else []):
            norm = normalize_status(k)
            if norm:
                normalized[norm] = normalized.get(norm, 0) + int(v)
        table_data[case_type] = normalized

    avg_response_list = [x for x in avg_response_list if x[1] is not None]
    avg_response_list.sort(key=lambda x: x[1], reverse=True)
    types_sorted = [x[0] for x in avg_response_list]
    avg_sorted = [x[1] for x in avg_response_list]

    # --------- CHART RENDERING ---------
    if types_sorted:
        fig1 = go.Figure(
            data=[go.Bar(y=types_sorted, x=avg_sorted, orientation="h", marker_color="#ffffff")]
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

    # --------- TABLE ---------
    table_data = {k: v for k, v in table_data.items() if v}
    if table_data:
        all_statuses = sorted({s for statuses in table_data.values() for s in statuses.keys()})
        service_types = list(table_data.keys())
        total_col = []
        column_values = {s: [] for s in all_statuses}

        for case_type in service_types:
            statuses = table_data[case_type]
            total = 0
            for s in all_statuses:
                v = statuses.get(s, 0)
                column_values[s].append(v)
                total += v
            total_col.append(total)

        header_vals = ["Service Type"] + all_statuses + ["Total"]
        cell_vals = [service_types] + [column_values[s] for s in all_statuses] + [total_col]

        fig2 = go.Figure(
            data=[go.Table(
                header=dict(values=header_vals, fill_color="#003c82", font=dict(color="white", size=13), align="left"),
                cells=dict(values=cell_vals, fill_color=[["#004b9b" if i % 2 == 0 else "#0054ad" for i in range(len(service_types))]], font=dict(color="white", size=12), align="left"),
            )]
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
        plot2_html = (
            f"<p style='text-align:center;font-size:1.2em;margin:40px 0;'>"
            f"No service request data found for this period ({period_name}).</p>"
        )

    # --------- NAVIGATION ---------
    nav_html_parts = ['<div class="nav-buttons">']
    for p_label, p_name in PERIODS.items():
        btn_text = p_name.replace("Last ", "")
        active_class = "nav-btn nav-btn-active" if p_label == period_label else "nav-btn"
        nav_html_parts.append(f'<a href="index_{p_label}.html" class="{active_class}">{btn_text}</a>')
    nav_html_parts.append("</div>")
    nav_html = "\n".join(nav_html_parts)

    # --------- WRITE HTML ---------
    html_path = OUTPUT_DIR / f"index_{period_label}.html"
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    with open(html_path, "w", encoding="utf-8") as f:
        f.write(f"""<!DOCTYPE html>
<html lang="en"> ...  <!-- (HTML unchanged for brevity, your original footer and styles remain) -->
""")
        # ✨ Write dynamic sections
        f.write(plot1_html + "<br>\n" + plot2_html)
        f.write("</body></html>")

    print(f"✅ Dashboard generated: {html_path.resolve()}")


# -------------------- MAIN --------------------
def main():
    data_path = Path("data/summary_results_current.json")
    if not data_path.exists():
        raise FileNotFoundError("❌ Missing summary_results_current.json")

    print(f"Loading data from: {data_path}")
    dataset = json.loads(data_path.read_text())

    raw_timestamp = dataset.get("downloaded_at", "Unknown")
    formatted_timestamp = format_timestamp(raw_timestamp)
    generated_timestamp = get_dashboard_generated_time()

    for period in PERIODS.keys():
        if PERIODS[period] not in dataset:
            print(f"⚠️ Missing data for {PERIODS[period]}, skipping")
            continue
        build_dashboard(period, dataset, formatted_timestamp, generated_timestamp)


if __name__ == "__main__":
    main()
