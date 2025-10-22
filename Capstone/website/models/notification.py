# website/models/notification.py

import logging
from datetime import datetime
import pytz
from bson import ObjectId
from flask import current_app
from .helpers import format_relative_time
import json
from pywebpush import webpush, WebPushException

logger = logging.getLogger(__name__)


# --- START OF MODIFICATION: Added Web Push Sending Logic ---

def _send_web_push_notification(subscriptions, payload_data):
    """
    Sends a web push notification to all provided subscriptions.
    """
    if not subscriptions:
        return

    try:
        vapid_private_key = current_app.config.get('VAPID_PRIVATE_KEY')
        vapid_claim_email = current_app.config.get('VAPID_CLAIM_EMAIL')

        if not vapid_private_key or not vapid_claim_email:
            logger.warning("VAPID keys are not configured. Cannot send web push notifications.")
            return

        for sub in subscriptions:
            try:
                webpush(
                    subscription_info=sub,
                    data=json.dumps(payload_data),
                    vapid_private_key=vapid_private_key,
                    vapid_claims={"sub": f"mailto:{vapid_claim_email}"}
                )
                logger.info(f"Successfully sent web push notification.")
            except WebPushException as ex:
                # This often happens if a subscription is expired or invalid.
                # You might want to add logic here to remove the subscription from the database.
                logger.error(f"WebPushException: {ex}")
                if ex.response and ex.response.status_code == 410:
                    logger.warning(f"Subscription has expired or is no longer valid: {sub.get('endpoint')}")

    except Exception as e:
        logger.error(f"An unexpected error occurred while sending web push notifications: {e}", exc_info=True)


def add_notification(username, title, message, url):
    db = current_app.db
    if db is None: return False
    try:
        # Locally import modules to prevent circular dependencies
        from website.utils.email_utils import send_notification_email
        from .user import get_user_by_username, get_user_push_subscriptions
        
        # 1. Save the notification to the database
        db.notifications.insert_one({
            'username': username,
            'title': title,
            'message': message,
            'url': url,
            'isRead': False,
            'createdAt': datetime.now(pytz.utc)
        })

        # 2. Send Email Notification
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
        
        # 3. Send Web Push Notification
        try:
            subscriptions = get_user_push_subscriptions(username)
            if subscriptions:
                push_payload = {
                    "title": title,
                    "body": message,
                    "icon": "/static/imgs/icons/logo.ico", # Optional: path to an icon
                    "data": {
                        "url": url
                    }
                }
                _send_web_push_notification(subscriptions, push_payload)
        except Exception as e:
            logger.error(f"Failed to trigger web push notification for user {username}: {e}")

        return True
    except Exception as e:
        logger.error(f"Error adding notification for {username}: {e}", exc_info=True)
        return False

# --- END OF MODIFICATION ---


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