# website/models/helpers.py

from datetime import datetime
import pytz

def format_relative_time(dt):
    """Formats a datetime object into a relative time string."""
    if not dt: return 'N/A'
    if dt.tzinfo is None:
        dt = pytz.utc.localize(dt)
    now = datetime.now(pytz.utc)
    diff = now - dt
    seconds = diff.total_seconds()
    if seconds < 60: return "just now"
    minutes = seconds / 60
    if minutes < 60: return f"{int(minutes)}m ago"
    hours = minutes / 60
    if hours < 24: return f"{int(hours)}h ago"
    days = hours / 24
    if days < 7: return f"{int(days)}d ago"
    return dt.strftime('%b %d, %Y')