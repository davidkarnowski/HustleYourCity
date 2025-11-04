#Generate about.html page from README.md Markdown file

import markdown
from pathlib import Path
from datetime import datetime
import pytz
import re

# Paths
README_PATH = Path("README.md")
OUTPUT_PATH = Path("data/dashboard/about.html")

# Read README
if not README_PATH.exists():
    raise FileNotFoundError("❌ README.md not found in project root.")

raw_md = README_PATH.read_text(encoding="utf-8")

# Remove the first image (banner) reference in markdown
clean_md = re.sub(r"!\[.*?\]\(.*?\)", "", raw_md, count=1).strip()

# Convert markdown → HTML
html_content = markdown.markdown(clean_md, extensions=["fenced_code", "tables"])

# Timestamp footer label
local_tz = pytz.timezone("America/Los_Angeles")
timestamp = datetime.now(local_tz).strftime("%B %d, %Y at %I:%M:%S %p %Z")

# Full styled HTML page
OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>About Hustle Long Beach</title>

<style>
  body {{
    background-color: #0054ad;
    color: white;
    font-family: 'Segoe UI', Arial, sans-serif;
    margin: 0;
    padding: 20px;
    line-height: 1.65em;
  }}
  h1, h2, h3, h4 {{
    color: white;
    margin-top: 25px;
    font-weight: 600;
  }}
  a {{
    color: white;
    text-decoration: underline;
  }}
  img {{
    max-width: 100%;
    border-radius: 10px;
  }}
  .container {{
    max-width: 900px;
    margin: auto;
    background: rgba(0,0,0,0.15);
    padding: 24px 32px;
    border-radius: 12px;
  }}
  ul li {{
    margin-bottom: 6px;
  }}
  pre, code {{
    background: rgba(255,255,255,0.08);
    padding: 10px;
    border-radius: 4px;
    display: block;
    font-size: 0.95em;
    overflow-x: auto;
  }}
  blockquote {{
    background: rgba(255,255,255,0.08);
    padding: 10px 15px;
    border-left: 4px solid white;
    border-radius: 6px;
    margin: 15px 0;
    font-style: italic;
  }}
  .footer {{
    margin-top: 40px;
    font-size: 0.9em;
    color: #e0e0e0;
    border-top: 1px solid #ffffff44;
    padding-top: 10px;
    text-align: center;
  }}
  .privacy-note {{
    font-size: 0.8em;
    color: #cccccc;
    margin-top: 8px;
    line-height: 1.4em;
  }}
  .back-link {{
    text-align: center;
    margin-bottom: 20px;
    display: block;
    font-size: 1.1em;
    font-weight: bold;
  }}
</style>

</head>
<body>

  <img src="Hustle_Long_Beach_Banner.png" alt="Hustle Long Beach Banner" class="banner">

  <a href="index_24hours.html" class="back-link">← Back to Current Dashboards</a>

  <div class="container">
{html_content}
  </div>

  <p style="text-align:center; margin:20px 0; font-size:0.9em;">
    Documentation generated on {timestamp}
  </p>

  <div style="text-align:center; margin:40px auto 20px auto; max-width:800px;">
    <h2 style="font-size:1.1em; font-weight:600; margin-bottom:0.75rem;">
      Support the continued development and maintenance of the Hustle Long Beach! project.<br>
      Any amount is appreciated and no PayPal account is required.
    </h2>

    <div>
      <style>.pp-JYJDUKNCD4324{{text-align:center;border:none;border-radius:0.25rem;min-width:11.625rem;padding:0 2rem;height:2.625rem;font-weight:bold;background-color:#FFD140;color:#000000;font-family:"Helvetica Neue",Arial,sans-serif;font-size:1rem;line-height:1.25rem;cursor:pointer;}}</style>
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
    <p>Disclaimer: This page is generated automatically from the project README and may update based on repository changes.</p>
    <p>Project Source: <a href="https://github.com/davidkarnowski/HustleYourCity" target="_blank">HustleYourCity on GitHub</a></p>
    <div class="privacy-note">
      Privacy & Transparency: This website does not use cookies, analytics, or trackers. No personal data is collected or stored by this site.
      Clicking the PayPal support link redirects to PayPal.com, which operates under its own privacy policy and may set its own cookies.
    </div>
  </div>

</body>
</html>
"""

# Write file
OUTPUT_PATH.write_text(html, encoding="utf-8")
print(f"✅ About page generated: {OUTPUT_PATH.resolve()}")
