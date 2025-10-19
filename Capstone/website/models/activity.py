# website/models/activity.py

import logging
from datetime import datetime
import pytz
from flask import current_app
from .helpers import format_relative_time

logger = logging.getLogger(__name__)

def log_user_activity(username, activity_type):
    db = current_app.db
    if db is None: return
    try:
        db.activity_logs.insert_one({
            'username': username,
            'activity_type': activity_type,
            'timestamp': datetime.now(pytz.utc)
        })
    except Exception as e:
        logger.error(f"Error logging user activity for {username}: {e}", exc_info=True)

def get_recent_activity(username, limit=10):
    db = current_app.db
    if db is None: return []
    activities = []
    try:
        for doc in db.activity_logs.find({'username': username}).sort('timestamp', -1).limit(limit):
            activities.append({
                'username': doc['username'].capitalize(),
                'relative_time': format_relative_time(doc['timestamp']),
                'activity_type': doc.get('activity_type', 'Unknown Action')
            })
    except Exception as e:
        logger.error(f"Error fetching recent activity for {username}: {e}", exc_info=True)
    return activities