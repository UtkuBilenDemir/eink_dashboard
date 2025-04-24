import requests
from datetime import datetime, timedelta
import os
import json
from collections import defaultdict
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import hydra
from hydra.core.global_hydra import GlobalHydra

# Load Hydra once
if not GlobalHydra.instance().is_initialized():
    hydra.initialize(config_path=".", version_base=None)
cfg = hydra.compose(config_name="config")

local_now = datetime.now(ZoneInfo("Europe/Vienna"))
start_of_today = local_now.replace(hour=0, minute=0, second=0, microsecond=0)
end_of_today = start_of_today + timedelta(days=1)

start_utc = start_of_today.astimezone(ZoneInfo("UTC"))
end_utc = end_of_today.astimezone(ZoneInfo("UTC"))

TOGGL_API_TOKEN = os.getenv("TOGGL_API_TOKEN", cfg.api.token)
WORKSPACE_ID = os.getenv("TOGGL_WORKSPACE_ID", cfg.api.workspace_id)
BASE_URL = cfg.api.base_url
MAX_DATE_RANGE_DAYS = cfg.settings.max_date_range_days
CACHE_FILE = "best_history_cache.json"
DAILY_GOAL_MIN = 390

TRACKING_START_DATE = datetime(2025, 4, 9, tzinfo=ZoneInfo("Europe/Vienna"))

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
        r = requests.get(
            url,
            params=params,
            auth=(TOGGL_API_TOKEN, 'api_token'),
            headers=get_headers(),
            timeout=30
        )
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
        current_start = current_end + timedelta(days=1)
    return entries

def total_minutes(entries):
    total = 0
    for e in entries:
        if e.get("stop") and e.get("start"):
            try:
                start = datetime.fromisoformat(e["start"].replace("Z", "+00:00"))
                stop = datetime.fromisoformat(e["stop"].replace("Z", "+00:00"))
                total += int((stop - start).total_seconds() / 60)
            except (ValueError, KeyError) as e:
                print(f"\u26a0\ufe0f Couldn't process entry: {e}")
    return total

def get_best_from_last_year():
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=365)
    entries = get_time_entries(start_date, end_date)
    if not entries:
        return (None, 0), (None, 0)
    by_day = defaultdict(int)
    by_week = defaultdict(int)
    for entry in entries:
        if not entry.get("stop") or not entry.get("start"):
            continue
        try:
            start = datetime.fromisoformat(entry["start"].replace("Z", "+00:00"))
            stop = datetime.fromisoformat(entry["stop"].replace("Z", "+00:00"))
            duration = (stop - start).total_seconds() / 60
            day_key = start.date().isoformat()
            by_day[day_key] += duration
            year, week, _ = start.isocalendar()
            week_key = f"{year}-W{week:02}"
            by_week[week_key] += duration
        except (ValueError, KeyError) as e:
            print(f"\u26a0\ufe0f Couldn't process entry: {e}")
            continue
    best_day_date = max(by_day, key=by_day.get, default=None)
    best_week_key = max(by_week, key=by_week.get, default=None)
    best_day = (best_day_date, int(by_day.get(best_day_date, 0)))
    best_week = (best_week_key, int(by_week.get(best_week_key, 0)))
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
        best_day, best_week = get_best_from_last_year()
        results["best_day"] = best_day if best_day[0] else ("No data", 0)
        results["best_week"] = best_week if best_week[0] else ("No data", 0)
    except Exception as e:
        print(f"\u26a0\ufe0f Error in productivity calculation: {str(e)}")
    return results

def get_total_debt():
    now = datetime.now(ZoneInfo("Europe/Vienna"))
    start = TRACKING_START_DATE

    # Count only weekdays
    total_weekdays = sum(
        1 for i in range((now.date() - start.date()).days + 1)
        if (start + timedelta(days=i)).weekday() < 5
    )

    required_minutes = total_weekdays * DAILY_GOAL_MIN
    actual_minutes = total_minutes(get_time_entries(
        start.astimezone(ZoneInfo("UTC")),
        now.astimezone(ZoneInfo("UTC"))
    ))

    return required_minutes - actual_minutes  # Allow surplus if overachieved

