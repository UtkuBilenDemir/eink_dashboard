from PIL import Image, ImageDraw, ImageFont
import time
import epd7in5_V2
import toggl

DAILY_GOAL_MIN = 390
WEEKLY_GOAL_MIN = DAILY_GOAL_MIN * 5

# Layout Constants
WIDTH, HEIGHT = 480, 800
X_MARGIN = 20
Y_MARGIN = 30
COL_SPACING = 210
LINE_HEIGHT = 26
SECTION_SPACING = 36
BAR_WIDTH = 100
BAR_HEIGHT = 14

# Fonts
font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
font = ImageFont.truetype(font_path, 22)
font_bold = ImageFont.truetype(font_path, 26)

# Utilities
def minutes_to_str(mins):
    if isinstance(mins, (tuple, list)):
        mins = mins[1]
    return f"{int(mins)//60}h {int(mins)%60}m"

def format_best(entry):
    return minutes_to_str(entry) if entry and entry[1] else "No data"

def draw_bar(draw, x, y, value, goal):
    ratio = min(value / goal, 1.0) if goal > 0 else 0
    fill_width = int(BAR_WIDTH * ratio)
    draw.rectangle([x, y, x + BAR_WIDTH, y + BAR_HEIGHT], outline=0)
    draw.rectangle([x, y, x + fill_width, y + BAR_HEIGHT], fill=0)

# Init display
epd = epd7in5_V2.EPD()
epd.init()
epd.Clear()

image = Image.new('1', (WIDTH, HEIGHT), 255)
draw = ImageDraw.Draw(image)

# Get data
data = toggl.get_productivity_data()
total_debt = toggl.get_total_debt()

today = data['today']
yesterday = data['yesterday']
best_day = data['best_day']
this_week = data['this_week']
last_week = data['last_week']
best_week = data['best_week']
debt_today = max(0, DAILY_GOAL_MIN - today)

# Draw section headers
y = Y_MARGIN
draw.text((X_MARGIN, y), "DAILY", font=font_bold, fill=0)
draw.text((X_MARGIN + COL_SPACING, y), "WEEKLY", font=font_bold, fill=0)
y += LINE_HEIGHT + 4

# Today & This Week bar
draw.text((X_MARGIN, y), "Today:", font=font, fill=0)
draw_bar(draw, X_MARGIN + 80, y + 2, today, DAILY_GOAL_MIN)
draw.text((X_MARGIN + COL_SPACING, y), "This Week:", font=font, fill=0)
draw_bar(draw, X_MARGIN + COL_SPACING + 130, y + 2, this_week, WEEKLY_GOAL_MIN)
y += BAR_HEIGHT + 8

# Other values
draw.text((X_MARGIN, y), f"Yest : {minutes_to_str(yesterday)}", font=font, fill=0)
draw.text((X_MARGIN + COL_SPACING, y), f"Last Week: {minutes_to_str(last_week)}", font=font, fill=0)
y += LINE_HEIGHT

draw.text((X_MARGIN, y), f"Best : {format_best(best_day)}", font=font, fill=0)
# draw.text((X_MARGIN + COL_SPACING, y), f"Best Week: {format_best(best_week)}", font=font, fill=0)
y += SECTION_SPACING

# Debt
draw.text((X_MARGIN, y), "DEBT", font=font_bold, fill=0)
y += LINE_HEIGHT + 4
draw.text((X_MARGIN, y), f"Owed Today: {minutes_to_str(debt_today)}", font=font, fill=0)
y += LINE_HEIGHT
draw.text((X_MARGIN, y), f"Since Apr 9: {minutes_to_str(total_debt)}", font=font, fill=0)

# Show image
epd.display(epd.getbuffer(image))
epd.sleep()
print(f"[{time.ctime()}] Dashboard updated successfully.")

