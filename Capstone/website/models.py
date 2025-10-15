# website/models.py

import bcrypt
from pymongo.errors import DuplicateKeyError
import logging
from datetime import datetime, timedelta
import pytz
from flask import current_app, url_for
import pyotp
import re
from bson.objectid import ObjectId
from calendar import month_name
import random
import string
# NOTE: Assumes constants are available, e.g., from a separate file or directly defined
from .constants import LOGIN_ATTEMPT_LIMIT, LOCKOUT_DURATION_MINUTES 

logger = logging.getLogger(__name__)

# --- Helper function for timestamps ---
def _format_relative_time(dt):
    """Formats a datetime object into a relative time string."""
    # Ensure dt (the stored timestamp) is timezone-aware
    if dt.tzinfo is None:
        dt = pytz.utc.localize(dt)

    # Ensure now (current time) is also timezone-aware (using UTC)
    now = datetime.now(pytz.utc)
    diff = now - dt

    seconds = diff.total_seconds()
    if seconds < 60:
        return "just now"
    minutes = seconds / 60
    if minutes < 60:
        return f"{int(minutes)}m ago"
    hours = minutes / 60
    if hours < 24:
        return f"{int(hours)}h ago"
    days = hours / 24
    if days < 7:
        return f"{int(days)}d ago"
    return dt.strftime('%b %d, %Y')


# =========================================================
# --- User & Auth Models ---
# =========================================================

def get_user_by_username(username):
    db = current_app.db
    if db is None: return None
    return db.users.find_one({'username': {'$regex': f'^{re.escape(username.strip().lower())}$', '$options': 'i'}})

def get_user_by_email(email):
    db = current_app.db
    if db is None: return None
    return db.users.find_one({'email': {'$regex': f'^{re.escape(email.strip().lower())}$', '$options': 'i'}})

def add_user(username, email, password):
    db = current_app.db
    if db is None: return False
    hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
    otp_secret = pyotp.random_base32()
    try:
        db.users.insert_one({
            'username': username.strip().lower(),
            'email': email.strip().lower(),
            'passwordHash': hashed_password,
            'isActive': False,
            'otpSecret': otp_secret,
            'createdAt': datetime.now(pytz.utc),
            'failedLoginAttempts': 0,
            'lockoutUntil': None,
            'lastLogin': None,
            'notes': ''
        })
        return True
    except DuplicateKeyError:
        return False

def check_password(stored_hash, provided_password):
    try:
        return bcrypt.checkpw(provided_password.encode('utf-8'), stored_hash)
    except (TypeError, ValueError):
        return False

def update_last_login(username):
    db = current_app.db
    if db is None: return
    db.users.update_one(
        {'username': {'$regex': f'^{re.escape(username.strip().lower())}$', '$options': 'i'}},
        {'$set': {'lastLogin': datetime.now(pytz.utc), 'failedLoginAttempts': 0, 'lockoutUntil': None}}
    )

def record_failed_login_attempt(username):
    db = current_app.db
    if db is None: return
    user = get_user_by_username(username)
    if not user: return

    new_attempts = user.get('failedLoginAttempts', 0) + 1
    update_fields = {'$set': {'failedLoginAttempts': new_attempts}}

    if new_attempts >= LOGIN_ATTEMPT_LIMIT:
        # Note: datetime.utcnow() is offset-naive, but using it with timedelta works.
        # However, for consistency, we should use datetime.now(pytz.utc)
        lockout_time = datetime.now(pytz.utc) + timedelta(minutes=LOCKOUT_DURATION_MINUTES)
        update_fields['$set']['lockoutUntil'] = lockout_time

    db.users.update_one({'_id': user['_id']}, update_fields)

def update_user_password(email, new_password):
    db = current_app.db
    if db is None: return False
    hashed_password = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt())
    result = db.users.update_one(
        {'email': {'$regex': f'^{re.escape(email.strip().lower())}$', '$options': 'i'}},
        {'$set': {'passwordHash': hashed_password}}
    )
    return result.matched_count == 1

def set_user_otp(username, otp_type='email'):
    db = current_app.db
    if db is None: return None
    user = get_user_by_username(username)
    if not user: return None
    if otp_type == 'email':
        otp = "".join(random.choices(string.digits, k=6))
        db.users.update_one({'_id': user['_id']}, {'$set': {'otp': otp, 'otpExpiresAt': datetime.now(pytz.utc) + timedelta(minutes=10)}})
        return otp
    return None

def verify_user_otp(username, submitted_otp, otp_type='email'):
    db = current_app.db
    if db is None: return False
    user = get_user_by_username(username)
    if not user: return False
    if otp_type == 'email':
        if user.get('otp') == submitted_otp and user.get('otpExpiresAt', datetime.min.replace(tzinfo=pytz.utc)) > datetime.now(pytz.utc):
            db.users.update_one({'_id': user['_id']}, {'$set': {'isActive': True}, '$unset': {'otp': "", 'otpExpiresAt': ""}})
            return True
    elif otp_type == '2fa':
        totp = pyotp.TOTP(user['otpSecret'])
        return totp.verify(submitted_otp, valid_window=1)
    return False


# =========================================================
# --- Activity Models ---
# =========================================================

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

def get_recent_activity(username, limit=3):
    db = current_app.db
    if db is None: return []
    activities = []
    try:
        for doc in db.activity_logs.find({'username': username}).sort('timestamp', -1).limit(limit):
            activities.append({
                'username': doc['username'].capitalize(),
                'relative_time': _format_relative_time(doc['timestamp']),
                'activity_type': doc.get('activity_type', 'Unknown Action') 
            })
    except Exception as e:
        # This error handling is critical for the previous TypeErrors
        logger.error(f"Error fetching recent activity for {username}: {e}", exc_info=True)
    return activities


# =========================================================
# --- Invoice Models (New) ---
# =========================================================

def add_invoice(username, branch, invoice_data, files):
    """Adds a new invoice record to the database."""
    db = current_app.db
    if db is None: return False
    try:
        # Note: 'files' should be a list of file info after saving them.
        db.invoices.insert_one({
            'username': username,
            'branch': branch,
            'folder_name': invoice_data.get('folder_name'),
            'category': invoice_data.get('category'),
            'date': invoice_data.get('date'),
            'files': files, # e.g., [{'filename': 'photo.png', 'path': '/uploads/...'}]
            'createdAt': datetime.now(pytz.utc)
        })
        return True
    except Exception as e:
        logger.error(f"Error adding invoice for {username}: {e}", exc_info=True)
        return False

def get_invoices(username, branch):
    """Fetches all invoices for a user and branch."""
    db = current_app.db
    if db is None: return []
    invoices = []
    try:
        query = {'username': username, 'branch': branch}
        for doc in db.invoices.find(query).sort('date', -1):
            # The 'date' field from the form is typically a string, 
            # but if it was stored as a datetime object in MongoDB, the strftime will work.
            invoices.append({
                'id': str(doc['_id']),
                'file_name': doc.get('folder_name', 'N/A'),
                'date': doc.get('date').strftime('%m/%d/%Y') if doc.get('date') else 'N/A',
                'category': doc.get('category', 'N/A')
            })
    except Exception as e:
        logger.error(f"Error fetching invoices for {username}: {e}", exc_info=True)
    return invoices


# =========================================================
# --- Transaction & Other Models ---
# =========================================================

def add_transaction(username, branch, transaction_data):
    db = current_app.db
    if db is None: return False
    try:
        check_date_obj = transaction_data.get('check_date')
        doc = {
            'username': username,
            'branch': branch,
            'name': transaction_data.get('name_of_issued_check'),
            'check_no': transaction_data.get('check_no'),
            'check_date': pytz.utc.localize(datetime.combine(check_date_obj, datetime.min.time())) if check_date_obj else datetime.now(pytz.utc),
            'countered_check': float(transaction_data.get('countered_check', 0.0)),
            'amount': float(transaction_data.get('countered_check', 0.0)),
            'ewt': float(transaction_data.get('ewt', 0.0)),
            'status': 'Pending',
            'sub_branch': 'San Isidro',
            'createdAt': datetime.now(pytz.utc),
            'isArchived': False,
            'notes': ''
        }
        db.transactions.insert_one(doc)
        return True
    except Exception as e:
        logger.error(f"Error adding transaction: {e}", exc_info=True)
        return False

def get_transactions_by_status(username, branch, status):
    db = current_app.db
    if db is None: return []
    transactions = []
    try:
        query = {
            'username': username,
            'status': status,
            '$or': [{'isArchived': {'$exists': False}}, {'isArchived': False}]
        }
        if branch:
            query['branch'] = branch

        for doc in db.transactions.find(query).sort('check_date', -1):
            transactions.append({
                '_id': str(doc['_id']),
                'name': doc.get('name'),
                'check_no': f"#{doc.get('check_no')}",
                'check_date': doc.get('check_date').strftime('%m/%d/%Y') if doc.get('check_date') else 'N/A',
                'ewt': f"₱ {doc.get('ewt', 0.0):,.2f}",
                'countered_check': f"₱ {doc.get('countered_check', 0.0):,.2f}",
                'editor': doc.get('username', 'Unknown').capitalize()
            })
    except Exception as e:
        logger.error(f"Error fetching transactions: {e}", exc_info=True)
    return transactions

def get_transaction_by_id(username, transaction_id):
    db = current_app.db
    if db is None: return None
    try:
        doc = db.transactions.find_one({'_id': ObjectId(transaction_id), 'username': username})
        if doc:
            return {
                '_id': str(doc['_id']),
                'name': doc.get('name'),
                'check_no': doc.get('check_no'),
                'check_date': doc.get('check_date').strftime('%Y-%m-%d') if doc.get('check_date') else '',
                'ewt': doc.get('ewt', 0.0),
                'countered_check': doc.get('countered_check', 0.0),
                'amount': doc.get('amount', 0.0),
                'notes': doc.get('notes', ''),
                'status': doc.get('status')
            }
    except Exception as e:
        logger.error(f"Error fetching transaction {transaction_id}: {e}", exc_info=True)
    return None

def mark_transaction_as_paid(username, transaction_id, notes=None):
    db = current_app.db
    if db is None: return False
    try:
        update_data = {'$set': {'status': 'Paid'}}
        if notes is not None:
            update_data['$set']['notes'] = notes
            
        result = db.transactions.update_one(
            {'_id': ObjectId(transaction_id), 'username': username},
            update_data
        )
        return result.modified_count == 1
    except Exception as e:
        logger.error(f"Error marking transaction {transaction_id} as paid: {e}", exc_info=True)
        return False

def archive_transaction(username, transaction_id):
    db = current_app.db
    if db is None: return False
    try:
        result = db.transactions.update_one(
            {'_id': ObjectId(transaction_id), 'username': username},
            {'$set': {'isArchived': True, 'archivedAt': datetime.now(pytz.utc)}}
        )
        return result.modified_count == 1
    except Exception as e:
        logger.error(f"Error archiving transaction {transaction_id}: {e}", exc_info=True)
        return False

def get_archived_items(username):
    db = current_app.db
    if db is None: return []
    items = []
    try:
        query = {'username': username, 'isArchived': True}
        for doc in db.transactions.find(query).sort('archivedAt', -1):
            items.append({
                'id': str(doc['_id']),
                'name': doc.get('name', 'N/A'),
                'details': f"Check #{doc.get('check_no', 'N/A')}",
                'archived_at_str': doc.get('archivedAt').strftime('%b %d, %Y, %I:%M %p') if doc.get('archivedAt') else 'N/A',
                'relative_time': _format_relative_time(doc.get('archivedAt')) if doc.get('archivedAt') else ''
            })
    except Exception as e:
        logger.error(f"Error fetching archived items: {e}", exc_info=True)
    return items

def get_analytics_data(username, year):
    db = current_app.db
    if db is None: return {}
    try:
        pipeline_monthly = [
            {'$match': {'username': username, 'status': 'Paid', 'check_date': {'$gte': datetime(year, 1, 1, tzinfo=pytz.utc), '$lt': datetime(year + 1, 1, 1, tzinfo=pytz.utc)}}},
            {'$group': {'_id': {'$month': '$check_date'}, 'total': {'$sum': '$amount'}}}
        ]
        monthly_totals = {doc['_id']: doc['total'] for doc in db.transactions.aggregate(pipeline_monthly)}
        current_month = datetime.now(pytz.utc).month
        start_of_current_month = datetime(year, current_month, 1, tzinfo=pytz.utc)
        start_of_next_month = datetime(year, current_month + 1, 1, tzinfo=pytz.utc) if current_month < 12 else datetime(year + 1, 1, 1, tzinfo=pytz.utc)
        pipeline_weekly = [
            {'$match': {'username': username, 'status': 'Paid', 'check_date': {'$gte': start_of_current_month, '$lt': start_of_next_month}}},
            {'$group': {'_id': {'$week': '$check_date'}, 'total': {'$sum': '$amount'}}},
            {'$sort': {'_id': 1}}
        ]
        weekly_agg = list(db.transactions.aggregate(pipeline_weekly))
        weekly_breakdown = [{'week': f"Week {i+1}", 'total': doc['total']} for i, doc in enumerate(weekly_agg)]
        total_year_earning = sum(monthly_totals.values())
        max_monthly_earning = max(monthly_totals.values()) if monthly_totals else 1
        chart_data = [
            {
                'month_name': month_name[i][:3],
                'total': monthly_totals.get(i, 0),
                'percentage': (monthly_totals.get(i, 0) / max_monthly_earning) * 100,
                'is_current_month': i == current_month
            } for i in range(1, 13)
        ]
        return {
            'year': year,
            'total_year_earning': total_year_earning,
            'chart_data': chart_data,
            'current_month_name': month_name[current_month].upper(),
            'weekly_breakdown': weekly_breakdown,
            'current_month_total': monthly_totals.get(current_month, 0)
        }
    except Exception as e:
        logger.error(f"Error generating analytics for {username} year {year}: {e}", exc_info=True)
        return {}


# =========================================================
# --- Notification and Push Subscription Models ---
# =========================================================

def add_notification(username, title, message, url):
    """Adds a new notification for a user to the database."""
    db = current_app.db
    if db is None: return False
    try:
        db.notifications.insert_one({
            'username': username,
            'title': title,
            'message': message,
            'url': url,
            'is_read': False,
            'timestamp': datetime.now(pytz.utc)
        })
        return True
    except Exception as e:
        logger.error(f"Error adding notification for {username}: {e}", exc_info=True)
        return False

def get_unread_notifications(username):
    """Fetches all unread notifications for a user."""
    db = current_app.db
    if db is None: return []
    notifications = []
    try:
        query = {'username': username, 'is_read': False}
        for doc in db.notifications.find(query).sort('timestamp', -1):
            notifications.append({
                'id': str(doc['_id']),
                'title': doc.get('title'),
                'message': doc.get('message'),
                'url': doc.get('url'),
                'relative_time': _format_relative_time(doc['timestamp'])
            })
    except Exception as e:
        logger.error(f"Error fetching unread notifications for {username}: {e}", exc_info=True)
    return notifications

def get_unread_notification_count(username):
    """Counts the number of unread notifications for a user."""
    db = current_app.db
    if db is None: return 0
    try:
        return db.notifications.count_documents({'username': username, 'is_read': False})
    except Exception as e:
        logger.error(f"Error counting notifications for {username}: {e}", exc_info=True)
        return 0

def mark_notifications_as_read(username):
    """Marks all unread notifications for a user as read."""
    db = current_app.db
    if db is None: return False
    try:
        db.notifications.update_many(
            {'username': username, 'is_read': False},
            {'$set': {'is_read': True}}
        )
        return True
    except Exception as e:
        logger.error(f"Error marking notifications as read for {username}: {e}", exc_info=True)
        return False

def save_push_subscription(username, subscription_info):
    """Saves a web push subscription for a user."""
    db = current_app.db
    if db is None: return False
    try:
        # Avoid duplicate subscriptions
        db.users.update_one(
            {'username': username},
            {'$addToSet': {'push_subscriptions': subscription_info}}
        )
        return True
    except Exception as e:
        logger.error(f"Error saving push subscription for {username}: {e}", exc_info=True)
        return False