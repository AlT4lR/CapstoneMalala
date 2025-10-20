# website/models/notification.py

import logging
from datetime import datetime
import pytz
from bson import ObjectId
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

def get_notifications(username, page=1, limit=25):
    """ Fetches notifications for a user with pagination. """
    db = current_app.db
    if db is None: return []
    try:
        skip_count = (page - 1) * limit
        notifications_cursor = db.notifications.find({'username': username}).sort('createdAt', -1).skip(skip_count).limit(limit)
        
        return [{
            'id': str(n['_id']),
            'title': n.get('title', 'Notification'),
            'message': n.get('message'),
            'url': n.get('url', '#'),
            'isRead': n.get('isRead', False), # Ensure isRead status is included
            'relative_time': format_relative_time(n['createdAt'])
        } for n in notifications_cursor]
    except Exception as e:
        logger.error(f"Error fetching notifications for {username}: {e}", exc_info=True)
        return []

def get_unread_notification_count(username):
    db = current_app.db
    if db is None: return 0
    try:
        return db.notifications.count_documents({'username': username, 'isRead': False})
    except Exception as e:
        logger.error(f"Error counting unread notifications for {username}: {e}", exc_info=True)
        return 0

def mark_single_notification_as_read(username, notification_id):
    """ Marks a single notification as read. """
    db = current_app.db
    if db is None: return False
    try:
        result = db.notifications.update_one(
            {'_id': ObjectId(notification_id), 'username': username},
            {'$set': {'isRead': True}}
        )
        return result.modified_count > 0
    except Exception as e:
        logger.error(f"Error marking notification {notification_id} as read for {username}: {e}", exc_info=True)
        return False