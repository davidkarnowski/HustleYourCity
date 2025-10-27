# generate_charts.py
from PIL import Image, ImageDraw, ImageFont
from pathlib import Path
import matplotlib.pyplot as plt
import matplotlib


def _load_standard_font(size: int) -> ImageFont.FreeTypeFont:
    """
    Load a standard, cross-platform font from Matplotlib's bundled fonts.
    This guarantees a valid TTF path on any system where Matplotlib is installed.
    """
    try:
        font_path = Path(matplotlib.get_data_path()) / "fonts/ttf/DejaVuSans.ttf"
        return ImageFont.truetype(str(font_path), size=size)
    except Exception as e:
        print(f"Warning: Could not load Matplotlib DejaVuSans font: {e}")
        print("Falling back to Pillow default font (non-scalable).")
        return ImageFont.load_default()


def create_and_enhance_chart(
    png_path: Path,
    service_types,
    avg_values,
    title: str,
    downloaded_at: str,
    logo_path: Path
):
    """
    Creates and enhances a chart PNG with:
      - Full Matplotlib chart render
      - A top logo banner
      - A fixed footer with static-size timestamp
    """
    # --- Configuration ---
    chart_bg = "#0054ad"
    footer_height = 75
    header_height = 160
    footer_font_size = 22  # Static font size, used consistently throughout

    # --- Create chart ---
    plt.figure(figsize=(8, max(2, 0.4 * len(service_types))))
    plt.barh(service_types, avg_values, color="#ffffff")

    ax = plt.gca()
    ax.set_facecolor(chart_bg)
    plt.gcf().set_facecolor(chart_bg)

    ax.tick_params(colors="white", labelsize=12)
    for spine in ax.spines.values():
        spine.set_color("white")

    plt.xlabel("Average Response Time (Hours)", color="white", fontsize=14)
    plt.ylabel("Service Type", color="white", fontsize=14)
    plt.title(title, color="white", fontsize=18, pad=20)
    plt.gca().invert_yaxis()
    plt.tight_layout()

    plt.savefig(png_path, facecolor=chart_bg, dpi=150)
    plt.close()

    # --- Add header + footer ---
    enhance_chart_with_footer(
        png_path=png_path,
        logo_path=logo_path,
        downloaded_at=downloaded_at,
        header_height=header_height,
        footer_height=footer_height,
        footer_font_size=footer_font_size,
    )


def enhance_chart_with_footer(
    png_path: Path,
    logo_path: Path,
    downloaded_at: str,
    header_height: int,
    footer_height: int,
    footer_font_size: int,
):
    """
    Expands chart canvas, adds logo, and renders static-size footer text
    using a guaranteed Matplotlib DejaVuSans TTF.
    """
    try:
        base_img = Image.open(png_path).convert("RGBA")
        width, height = base_img.size
        new_height = height + header_height + footer_height
        new_img = Image.new("RGBA", (width, new_height), "#0054ad")

        # --- Header logo (optional) ---
        if logo_path and Path(logo_path).exists():
            try:
                logo = Image.open(logo_path).convert("RGBA")
                logo_width = int(width * 0.75)
                ratio = logo_width / logo.width
                logo = logo.resize((logo_width, int(logo.height * ratio)), Image.LANCZOS)
                logo_x = (width - logo.width) // 2
                logo_y = (header_height - logo.height) // 2
                new_img.paste(logo, (logo_x, logo_y), mask=logo)
            except Exception as e:
                print(f"Logo overlay failed: {e}")

        # --- Paste chart ---
        new_img.paste(base_img, (0, header_height))

        # --- Footer text ---
        draw = ImageDraw.Draw(new_img)
        font = _load_standard_font(footer_font_size)

        text = f"Data as of {downloaded_at}"
        text_x = 40

        # Compute vertical centering within footer
        ascent, descent = font.getmetrics()
        text_height = ascent + descent
        text_y = header_height + height + (footer_height - text_height) // 2

        draw.text((text_x, text_y), text, fill="white", font=font)

        new_img.save(png_path)
        print(f"Chart rendered and enhanced: {png_path}")

    except Exception as e:
        print(f"Chart enhancement failed for {png_path}: {e}")
