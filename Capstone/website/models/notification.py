# website/models/notification.py

import logging
from datetime import datetime
import pytz
from flask import current_app
from .helpers import format_relative_time

logger = logging.getLogger(__name__)

def add_notification(username, title, message, url):
    db = current_app.db
    if db is None: return False
    try:
        db.notifications.insert_one({
            'username': username,
            'title': title,
            'message': message,
            'url': url,
            'isRead': False,
            'createdAt': datetime.now(pytz.utc)
        })
        return True
    except Exception as e:
        logger.error(f"Error adding notification for {username}: {e}", exc_info=True)
        return False

def get_unread_notifications(username, limit=10):
    db = current_app.db
    if db is None: return []
    try:
        notifications = list(db.notifications.find({'username': username}).sort('createdAt', -1).limit(limit))
        return [{
            'id': str(n['_id']),
            'title': n.get('title', 'Notification'),
            'message': n.get('message'),
            'url': n.get('url', '#'),
            'isRead': n.get('isRead'),
            'relative_time': format_relative_time(n['createdAt'])
        } for n in notifications]
    except Exception as e:
        logger.error(f"Error fetching unread notifications for {username}: {e}", exc_info=True)
        return []

def get_unread_notification_count(username):
    db = current_app.db
    if db is None: return 0
    try:
        return db.notifications.count_documents({'username': username, 'isRead': False})
    except Exception as e:
        logger.error(f"Error counting unread notifications for {username}: {e}", exc_info=True)
        return 0

def mark_notifications_as_read(username):
    db = current_app.db
    if db is None: return 0
    try:
        result = db.notifications.update_many({'username': username, 'isRead': False}, {'$set': {'isRead': True}})
        return result.modified_count
    except Exception as e:
        logger.error(f"Error marking notifications as read for {username}: {e}", exc_info=True)
        return 0