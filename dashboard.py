from PIL import Image, ImageDraw, ImageFont
import time
import epd7in5_V2
import toggl

DAILY_GOAL_MIN = 390
WEEKLY_GOAL_MIN = DAILY_GOAL_MIN * 5

# Layout Constants
BAR_WIDTH = 280
BAR_HEIGHT = 16
LINE_HEIGHT = 26
LINE_SPACING = 12
X_MARGIN = 20
X_BAR = 160
Y_START = 30

# Fonts
font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
font = ImageFont.truetype(font_path, 22)
font_bold = ImageFont.truetype(font_path, 26)

# Utility
def minutes_to_str(mins):
    """Handle both numbers and (date, minutes) tuples"""
    if isinstance(mins, (tuple, list)):
        mins = mins[1]  # Extract minutes from tuple
    return f"{mins//60}h {mins%60}m"

def format_best_entry(entry):
    """Format best day/week entry with date and time"""
    if not entry or not entry[0]:
        return "No data"
    return f"{entry[0]} ({minutes_to_str(entry)})"

def draw_label_value(draw, label, value, y):
    draw.text((X_MARGIN, y), f"{label}: {value}", font=font, fill=0)
    return y + LINE_HEIGHT + LINE_SPACING

def draw_label_bar(draw, label, value_str, minutes, goal, y):
    # Label and value on same line
    draw.text((X_MARGIN, y), f"{label}: {value_str}", font=font, fill=0)
    y += LINE_HEIGHT
    # Progress bar
    ratio = min(minutes / goal, 1.0)
    draw.rectangle([X_BAR, y, X_BAR + BAR_WIDTH, y + BAR_HEIGHT], outline=0)
    draw.rectangle([X_BAR, y, X_BAR + int(BAR_WIDTH * ratio), y + BAR_HEIGHT], fill=0)
    return y + BAR_HEIGHT + LINE_SPACING

# Init display
epd = epd7in5_V2.EPD()
epd.init()
epd.Clear()

image = Image.new('1', (480, 800), 255)
draw = ImageDraw.Draw(image)

# Get data
data = toggl.get_productivity_data()

# Draw sections
y = Y_START
draw.text((X_MARGIN, y), "DAILY OVERVIEW", font=font_bold, fill=0)
y += LINE_HEIGHT + LINE_SPACING

y = draw_label_bar(draw, "Today", minutes_to_str(data['today']), data['today'], DAILY_GOAL_MIN, y)
y = draw_label_value(draw, "Yesterday", minutes_to_str(data['yesterday']), y)
y = draw_label_value(draw, "Best Day", format_best_entry(data['best_day']), y)

y += LINE_HEIGHT
draw.text((X_MARGIN, y), "WEEKLY OVERVIEW", font=font_bold, fill=0)
y += LINE_HEIGHT + LINE_SPACING

y = draw_label_bar(draw, "This Week", minutes_to_str(data['this_week']), data['this_week'], WEEKLY_GOAL_MIN, y)
y = draw_label_value(draw, "Last Week", minutes_to_str(data['last_week']), y)
y = draw_label_value(draw, "Best Week", format_best_entry(data['best_week']), y)

y += LINE_HEIGHT
draw.text((X_MARGIN, y), "PRODUCTIVITY DEBT", font=font_bold, fill=0)
y += LINE_HEIGHT + LINE_SPACING

debt = DAILY_GOAL_MIN - data['today']
if debt > 0:
    draw.text((X_MARGIN, y), f"You owe: {minutes_to_str(debt)} today", font=font, fill=0)
else:
    draw.text((X_MARGIN, y), "✅ Daily goal reached!", font=font, fill=0)

# Show image
epd.display(epd.getbuffer(image))
epd.sleep()
print(f"[{time.ctime()}] Dashboard updated successfully.")
