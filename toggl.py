import requests
from datetime import datetime, timedelta
import os
from collections import defaultdict
from zoneinfo import ZoneInfo
import hydra
from hydra.core.global_hydra import GlobalHydra

# Hydra Config
if not GlobalHydra.instance().is_initialized():
    hydra.initialize(config_path=".", version_base=None)
cfg = hydra.compose(config_name="config")

# Constants
TOGGL_API_TOKEN = os.getenv("TOGGL_API_TOKEN", cfg.api.token)
WORKSPACE_ID = os.getenv("TOGGL_WORKSPACE_ID", cfg.api.workspace_id)
BASE_URL = cfg.api.base_url
MAX_DATE_RANGE_DAYS = cfg.settings.max_date_range_days
DAILY_GOAL_MIN = 390
TRACKING_START_DATE = datetime(2025, 4, 9, tzinfo=ZoneInfo("Europe/Vienna"))

# Helper Functions
def iso(dt):
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")

def get_headers():
    return {
        "Content-Type": "application/json",
        "User-Agent": "Toggl Productivity Tracker/1.0"
    }

def get_time_entries(start_date, end_date):
    if (end_date - start_date).days > MAX_DATE_RANGE_DAYS:
        return get_time_entries_chunked(start_date, end_date)

    url = f"{BASE_URL}/me/time_entries"
    params = {
        "start_date": iso(start_date),
        "end_date": iso(end_date)
    }
    try:
        r = requests.get(url, params=params, auth=(TOGGL_API_TOKEN, 'api_token'), headers=get_headers(), timeout=30)
        r.raise_for_status()
        return r.json()
    except requests.exceptions.RequestException as e:
        print(f"\u26a0\ufe0f API request failed: {str(e)}")
        return []

def get_time_entries_chunked(start_date, end_date):
    entries = []
    current_start = start_date
    while current_start < end_date:
        current_end = min(current_start + timedelta(days=MAX_DATE_RANGE_DAYS), end_date)
        chunk = get_time_entries(current_start, current_end)
        entries.extend(chunk)
        current_start = current_end + timedelta(seconds=1)
    return entries

def total_minutes(entries):
    total = 0
    for e in entries:
        if e.get("stop") and e.get("start"):
            try:
                start = datetime.fromisoformat(e["start"].replace("Z", "+00:00"))
                stop = datetime.fromisoformat(e["stop"].replace("Z", "+00:00"))
                total += int((stop - start).total_seconds() / 60)
            except Exception as ex:
                print(f"\u26a0\ufe0f Couldn't process entry: {ex}")
    return total

def get_best_from_start():
    end_date = datetime.now(ZoneInfo("Europe/Vienna"))
    entries = get_time_entries(TRACKING_START_DATE.astimezone(ZoneInfo("UTC")), end_date.astimezone(ZoneInfo("UTC")))

    if not entries:
        return (None, 0), (None, 0)

    by_day = defaultdict(int)
    by_week = defaultdict(int)

    for entry in entries:
        if not entry.get("stop") or not entry.get("start"):
            continue
        try:
            start = datetime.fromisoformat(entry["start"].replace("Z", "+00:00")).astimezone(ZoneInfo("Europe/Vienna"))
            stop = datetime.fromisoformat(entry["stop"].replace("Z", "+00:00")).astimezone(ZoneInfo("Europe/Vienna"))
            duration = int((stop - start).total_seconds() / 60)
            
            # Group by day
            day_key = start.date().isoformat()
            by_day[day_key] += duration

            # Group by ISO week
            year, week, _ = start.isocalendar()
            week_key = f"{year}-W{week:02}"
            by_week[week_key] += duration

        except Exception as ex:
            print(f"\u26a0\ufe0f Entry parsing error: {ex}")
            continue

    best_day_key = max(by_day, key=by_day.get, default=None)
    best_week_key = max(by_week, key=by_week.get, default=None)

    best_day = (best_day_key, int(by_day.get(best_day_key, 0)))
    best_week = (best_week_key, int(by_week.get(best_week_key, 0)))

    # Debug print
    print("\U0001F4CA Top 5 weeks:")
    for week, minutes in sorted(by_week.items(), key=lambda x: x[1], reverse=True)[:5]:
        print(f"{week}: {minutes//60}h {minutes%60}m")

    return best_day, best_week

def get_productivity_data():
    local_tz = ZoneInfo("Europe/Vienna")
    now_local = datetime.now(local_tz)

    start_of_today = now_local.replace(hour=0, minute=0, second=0, microsecond=0)
    end_of_today = start_of_today + timedelta(days=1)
    start_of_yesterday = start_of_today - timedelta(days=1)
    end_of_yesterday = start_of_today
    start_of_this_week = start_of_today - timedelta(days=start_of_today.weekday())
    end_of_this_week = start_of_this_week + timedelta(days=7)
    start_of_last_week = start_of_this_week - timedelta(days=7)
    end_of_last_week = start_of_this_week

    def utc(dt): return dt.astimezone(ZoneInfo("UTC"))

    results = {
        "today": 0,
        "yesterday": 0,
        "this_week": 0,
        "last_week": 0,
        "best_day": ("No data", 0),
        "best_week": ("No data", 0)
    }

    try:
        results["today"] = int(total_minutes(get_time_entries(utc(start_of_today), utc(end_of_today))))
        results["yesterday"] = int(total_minutes(get_time_entries(utc(start_of_yesterday), utc(end_of_yesterday))))
        results["this_week"] = int(total_minutes(get_time_entries(utc(start_of_this_week), utc(now_local))))
        results["last_week"] = int(total_minutes(get_time_entries(utc(start_of_last_week), utc(end_of_last_week))))

        best_day, best_week = get_best_from_start()
        results["best_day"] = best_day if best_day[0] else ("No data", 0)
        results["best_week"] = best_week if best_week[0] else ("No data", 0)

    except Exception as e:
        print(f"\u26a0\ufe0f Error in productivity calculation: {str(e)}")

    return results

def get_total_debt():
    now = datetime.now(ZoneInfo("Europe/Vienna"))
    start = TRACKING_START_DATE

    total_weekdays = sum(
        1 for i in range((now.date() - start.date()).days + 1)
        if (start + timedelta(days=i)).weekday() < 5
    )

    required_minutes = total_weekdays * DAILY_GOAL_MIN
    actual_minutes = total_minutes(get_time_entries(
        start.astimezone(ZoneInfo("UTC")),
        now.astimezone(ZoneInfo("UTC"))
    ))

    return required_minutes - actual_minutes

