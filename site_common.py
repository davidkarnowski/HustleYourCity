"""Page pieces shared by every generated page (live dashboards and the archive page)."""

# Clicking the banner returns to the site's front page (which opens the current 1-day dashboard).
BANNER_HTML = (
    '<a href="/" class="banner-link" aria-label="Hustle Long Beach home">'
    '<img src="Hustle_Long_Beach_Banner.png" alt="Hustle Long Beach Banner" class="banner"></a>'
)

# PayPal support block, identical on every page.
SUPPORT_HTML = """
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
"""

PRIVACY_NOTE = (
    "Privacy & Transparency: This website does not use cookies, analytics, or trackers. No personal data is "
    "collected or stored by this site. Clicking the PayPal support link redirects to PayPal.com, which operates "
    "under its own privacy policy and may set its own cookies."
)
