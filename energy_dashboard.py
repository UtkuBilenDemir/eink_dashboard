from datetime import datetime, timedelta
from collections import defaultdict
from PIL import Image, ImageDraw, ImageFont
from zoneinfo import ZoneInfo
from omegaconf import OmegaConf
import epd7in5_V2

# Load config
cfg = OmegaConf.load("config.yaml")

# Constants
DAILY_FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
WIDTH, HEIGHT = 480, 800
BAR_WIDTH = 280
BAR_HEIGHT = 18
LINE_HEIGHT = 26
X_MARGIN = 20
Y_START = 20
TEXT_COLOR = 0
BG_COLOR = 255

def get_monthly_summary(entries, start_kwh, price_cents):
    records = [(datetime.strptime(e["date"], "%Y-%m-%d"), e["reading_kwh"]) for e in entries]
    records.sort()
    monthly_usage = defaultdict(float)
    previous = start_kwh
    for date, reading in records:
        month_key = date.strftime("%Y-%m")
        usage = reading - previous
        monthly_usage[month_key] += usage
        previous = reading
    monthly_costs = {k: round(v * price_cents / 100, 2) for k, v in monthly_usage.items()}
    return monthly_usage, monthly_costs

def draw_bar(draw, label, usage, cost, y, bold=False):
    font = ImageFont.truetype(DAILY_FONT, 22)
    font_bold = ImageFont.truetype(DAILY_FONT, 26)
    f = font_bold if bold else font
    bar_len = min(int(cost * 5), BAR_WIDTH)
    draw.text((X_MARGIN, y), label, font=f, fill=TEXT_COLOR)
    draw.rectangle([240, y + 5, 240 + bar_len, y + 5 + BAR_HEIGHT], fill=0)
    draw.text((240 + bar_len + 10, y), f"€{cost:.2f}", font=font, fill=TEXT_COLOR)
    return y + LINE_HEIGHT + 10

def render_dashboard():
    epd = epd7in5_V2.EPD()
    epd.init()
    epd.Clear()

    image = Image.new('1', (WIDTH, HEIGHT), BG_COLOR)
    draw = ImageDraw.Draw(image)
    bold = ImageFont.truetype(DAILY_FONT, 26)

    y = Y_START
    draw.text((X_MARGIN, y), "Monthly Electricity Summary", font=bold, fill=TEXT_COLOR)
    y += LINE_HEIGHT + 10

    tariff = cfg.energy.tariffs.electricity
    readings = cfg.energy.readings.electricity

    usage, costs = get_monthly_summary(
        readings.entries,
        readings.start_reading_kwh,
        tariff.price_cents_per_kwh
    )

    now = datetime.now(ZoneInfo("Europe/Vienna"))
    current_month = now.strftime("%Y-%m")
    last_month = (now.replace(day=1) - timedelta(days=1)).strftime("%Y-%m")
    best_month = min(costs.items(), key=lambda x: x[1], default=(None, 0))

    if current_month in costs:
        y = draw_bar(draw, f"This Month ({current_month})", usage[current_month], costs[current_month], y, True)
    if last_month in costs:
        y = draw_bar(draw, f"Last Month ({last_month})", usage[last_month], costs[last_month], y)
    if best_month[0]:
        y = draw_bar(draw, f"🏆 Best Month ({best_month[0]})", usage[best_month[0]], best_month[1], y)

    epd.display(epd.getbuffer(image))
    epd.sleep()
    print(f"[{datetime.now()}] Dashboard updated.")

if __name__ == "__main__":
    render_dashboard()
