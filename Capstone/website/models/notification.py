# website/models/notification.py

import logging
from datetime import datetime
import pytz
from bson import ObjectId
from flask import current_app
from .helpers import format_relative_time
# The problematic top-level import has been removed from here.

logger = logging.getLogger(__name__)

def add_notification(username, title, message, url):
    db = current_app.db
    if db is None: return False
    try:
        # --- START OF FIX ---
        # Import the necessary modules locally, only when this function is called.
        from website.utils.email_utils import send_notification_email
        from .user import get_user_by_username
        # --- END OF FIX ---
        
        db.notifications.insert_one({
            'username': username,
            'title': title,
            'message': message,
            'url': url,
            'isRead': False,
            'createdAt': datetime.now(pytz.utc)
        })

        # --- Email Sending Logic ---
        try:
            user = get_user_by_username(username)
            if user and user.get('email'):
                subject = f"[DecoOffice] Notification: {title}"
                send_notification_email(
                    recipient_email=user['email'],
                    subject=subject,
                    title=title,
                    message=message,
                    url=url
                )
        except Exception as e:
            logger.error(f"Failed to trigger email notification for user {username}: {e}")
        
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
            'isRead': n.get('isRead', False),
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