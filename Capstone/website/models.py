import bcrypt
from pymongo.errors import DuplicateKeyError
import logging
from datetime import datetime, timedelta
import random
import string
import pyotp
import pytz
from flask import current_app
from website.constants import LOGIN_ATTEMPT_LIMIT as LOCKOUT_THRESHOLD, LOCKOUT_DURATION_MINUTES
import re
from bson.objectid import ObjectId
from bson.errors import InvalidId

logger = logging.getLogger(__name__)

DEFAULT_SCHEDULE_CATEGORIES = ['Office', 'Meetings', 'Events', 'Personal', 'Others']

# --- User Operations ---
def get_user_by_username(username):
    db = current_app.db
    if db is None:
        logger.error("Database not available.")
        return None
    return db.users.find_one({'username': {'$regex': f'^{re.escape(username.strip().lower())}$', '$options': 'i'}})

def get_user_by_email(email):
    db = current_app.db
    if db is None:
        logger.error("Database not available.")
        return None
    return db.users.find_one({'email': {'$regex': f'^{re.escape(email.strip().lower())}$', '$options': 'i'}})

def update_user_password(email, new_password):
    """Securely updates a user's password hash, used for password reset."""
    db = current_app.db
    if db is None:
        logger.error("Database not available. Cannot update password.")
        return False
    try:
        new_hashed_password = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt())
        result = db.users.update_one(
            {'email': {'$regex': f'^{re.escape(email.strip().lower())}$', '$options': 'i'}},
            {'$set': {'passwordHash': new_hashed_password, 'updatedAt': datetime.now(pytz.utc)}}
        )
        if result.matched_count == 1:
            logger.info(f"Successfully updated password for user with email: {email}")
            return True
        else:
            logger.warning(f"Attempted to update password for non-existent email: {email}")
            return False
    except Exception as e:
        logger.error(f"Error updating password for {email}: {e}", exc_info=True)
        return False

def add_user(username, email, password):
    db = current_app.db
    if db is None: return False
    hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
    otp_secret = pyotp.random_base32()
    user_data = {
        'username': username.strip().lower(), 'email': email.strip().lower(), 'passwordHash': hashed_password,
        'role': 'user', 'isActive': False, 'otp': None, 'otpExpiresAt': None, 'otpSecret': otp_secret,
        'failedLoginAttempts': 0, 'lockoutUntil': None, 'lastLogin': None,
        'createdAt': datetime.now(pytz.utc), 'updatedAt': datetime.now(pytz.utc)
    }
    try:
        db.users.insert_one(user_data)
        logger.info(f"Successfully registered user: {user_data['username']}.")
        return True
    except DuplicateKeyError:
        logger.warning(f"Registration failed: Username '{username}' or Email '{email}' already exists.")
        return False
    except Exception as e:
        logger.error(f"Unexpected error during registration: {e}")
        return False

def check_password(stored_hash, provided_password):
    try:
        return bcrypt.checkpw(provided_password.encode('utf-8'), stored_hash)
    except (TypeError, ValueError):
        logger.error("Invalid password hash format encountered.")
        return False

def update_last_login(username):
    db = current_app.db
    if db is None: return
    try:
        db.users.update_one(
            {'username': {'$regex': f'^{re.escape(username.strip().lower())}$', '$options': 'i'}},
            {'$set': {'lastLogin': datetime.now(pytz.utc), 'failedLoginAttempts': 0, 'lockoutUntil': None, 'updatedAt': datetime.now(pytz.utc)}}
        )
    except Exception as e:
        logger.error(f"Error updating last login for {username}: {e}")

def record_failed_login_attempt(username):
    db = current_app.db
    if db is None: return
    user = get_user_by_username(username)
    if not user: return
    new_attempts = user.get('failedLoginAttempts', 0) + 1
    update_fields = {'failedLoginAttempts': new_attempts, 'updatedAt': datetime.now(pytz.utc)}
    if new_attempts >= LOCKOUT_THRESHOLD:
        lockout_time = datetime.utcnow() + timedelta(minutes=LOCKOUT_DURATION_MINUTES)
        update_fields['lockoutUntil'] = lockout_time
        logger.warning(f"User '{username}' locked out until {lockout_time}.")
    try:
        db.users.update_one({'_id': user['_id']}, {'$set': update_fields})
    except Exception as e:
        logger.error(f"Error recording failed login attempt for {username}: {e}")

def set_user_otp(username, otp_type='email'):
    db = current_app.db
    if db is None: return None
    user = get_user_by_username(username)
    if not user: return None
    if otp_type == 'email':
        otp = "".join(random.choices(string.digits, k=6))
        otp_expiration = datetime.now(pytz.utc) + timedelta(minutes=10)
        try:
            db.users.update_one(
                {'_id': user['_id']},
                {'$set': {'otp': otp, 'otpExpiresAt': otp_expiration, 'updatedAt': datetime.now(pytz.utc)}}
            )
            logger.info(f"Generated email OTP for user '{username}'.")
            return otp
        except Exception as e:
            logger.error(f"Error setting email OTP for {username}: {e}")
            return None
    return None

def verify_user_otp(username, submitted_otp, otp_type='email'):
    db = current_app.db
    if db is None: return False
    user = get_user_by_username(username)
    if not user: return False
    if otp_type == 'email':
        otp_expires_at = user.get('otpExpiresAt')
        if otp_expires_at and otp_expires_at.tzinfo is None:
            otp_expires_at = pytz.utc.localize(otp_expires_at)
        if user.get('otp') == submitted_otp and otp_expires_at and otp_expires_at > datetime.now(pytz.utc):
            try:
                db.users.update_one(
                    {'_id': user['_id']},
                    {'$set': {'isActive': True, 'updatedAt': datetime.now(pytz.utc)},
                     '$unset': {'otp': "", 'otpExpiresAt': ""}}
                )
                logger.info(f"User '{username}' verified via email OTP and activated.")
                return True
            except Exception as e:
                logger.error(f"Error activating user '{username}': {e}")
                return False
        else:
            return False
    elif otp_type == '2fa':
        otp_secret = user.get('otpSecret')
        if not otp_secret or not submitted_otp: return False
        totp = pyotp.TOTP(otp_secret)
        return totp.verify(submitted_otp, valid_window=1)
    return False

# --- Zoho Token Management ---
def save_zoho_tokens(username, token_data):
    db = current_app.db
    if not db: return False
    try:
        update_fields = {
            'zoho_access_token': token_data['access_token'],
            'zoho_token_expires_at': token_data.get('expires_at'),
            'updatedAt': datetime.now(pytz.utc)
        }
        if 'refresh_token' in token_data:
            update_fields['zoho_refresh_token'] = token_data['refresh_token']
        
        db.users.update_one({'username': username}, {'$set': update_fields})
        logger.info(f"Saved Zoho tokens for user '{username}'.")
        return True
    except Exception as e:
        logger.error(f"Error saving Zoho tokens for {username}: {e}", exc_info=True)
        return False

def get_zoho_tokens(username):
    user = get_user_by_username(username)
    if not user: return None
    return {
        'access_token': user.get('zoho_access_token'),
        'refresh_token': user.get('zoho_refresh_token'),
        'expires_at': user.get('zoho_token_expires_at'),
        'primary_calendar_id': user.get('zoho_primary_calendar_id')
    }

def save_primary_calendar(username, calendar_id):
    db = current_app.db
    if not db: return False
    try:
        db.users.update_one(
            {'username': username},
            {'$set': {'zoho_primary_calendar_id': calendar_id, 'updatedAt': datetime.now(pytz.utc)}}
        )
        return True
    except Exception as e:
        logger.error(f"Error saving primary calendar for {username}: {e}", exc_info=True)
        return False
        
def get_all_categories(username):
    """Returns the default list of categories for the UI, as they aren't stored in Zoho."""
    return DEFAULT_SCHEDULE_CATEGORIES


# --- Transaction Operations ---
def add_transaction(username, branch, transaction_data):
    db = current_app.db
    if db is None: return False
    try:
        check_date_obj = transaction_data.get('check_date')
        # Ensure date is stored as a proper BSON date
        datetime_utc = datetime.combine(check_date_obj, datetime.min.time()) if isinstance(check_date_obj, datetime.date) else None

        doc = {
            'username': username,
            'branch': branch,
            'name': transaction_data.get('name_of_issued_check'),
            'check_no': transaction_data.get('check_no'),
            'check_date': datetime_utc,
            'countered_check': float(transaction_data.get('countered_check', 0.0)),
            'amount': float(transaction_data.get('check_amount')),
            'ewt': float(transaction_data.get('ewt', 0.0)),
            'method': transaction_data.get('payment_method'),
            'status': transaction_data.get('status'),
            'notes': transaction_data.get('notes', ''),
            'createdAt': datetime.now(pytz.utc),
            'updatedAt': datetime.now(pytz.utc)
        }
        db.transactions.insert_one(doc)
        logger.info(f"Transaction {doc['check_no']} added successfully for user '{username}'.")
        return True
    except Exception as e:
        logger.error(f"Error adding transaction for user {username}: {e}", exc_info=True)
        return False

def get_transactions_by_status(username, branch, status):
    db = current_app.db
    if db is None: return []
    query = {'username': username, 'branch': branch, 'status': status}
    transactions = []
    try:
        for doc in db.transactions.find(query).sort('check_date', -1):
            check_date = doc.get('check_date')
            transactions.append({
                '_id': str(doc.get('_id')),
                'name': doc.get('name'),
                'check_no': doc.get('check_no'),
                'check_date': check_date.strftime('%m/%d/%Y') if check_date else 'N/A',
                'countered': f"₱ {doc.get('countered_check', 0.0):,.2f}",
                'amount': doc.get('amount', 0.0),
                'ewt': f"₱ {doc.get('ewt', 0.0):,.2f}",
                'status': doc.get('status')
            })
    except Exception as e:
        logger.error(f"Error fetching transactions for {username}: {e}", exc_info=True)
    return transactions


def delete_transaction(username, transaction_id):
    db = current_app.db
    if db is None: return False
    try:
        result = db.transactions.delete_one({'_id': ObjectId(transaction_id), 'username': username})
        if result.deleted_count == 1:
            logger.info(f"Transaction '{transaction_id}' deleted successfully for user '{username}'.")
            return True
        else:
            logger.warning(f"Transaction '{transaction_id}' not found or user '{username}' lacks permission.")
            return False
    except InvalidId:
        logger.error(f"Invalid transaction ID format: {transaction_id}")
        return False
    except Exception as e:
        logger.error(f"Error deleting transaction {transaction_id} for user {username}: {e}", exc_info=True)
        return False

def get_transaction_by_id(username, transaction_id):
    db = current_app.db
    if db is None: return None
    try:
        doc = db.transactions.find_one({'_id': ObjectId(transaction_id), 'username': username})
        if doc:
            dt = doc.get('check_date')
            return {
                '_id': str(doc.get('_id')), 'id': doc.get('check_no'), 'name': doc.get('name'),
                'delivery_date_full': dt.strftime('%m/%d/%Y %I:%M %p') if dt else 'N/A',
                'check_date_only': dt.strftime('%m/%d/%Y') if dt else 'N/A',
                'amount': doc.get('amount'), 'method': doc.get('method', 'N/A'),
                'status': doc.get('status'), 'notes': doc.get('notes', 'No notes provided.')
            }
        return None
    except InvalidId:
        return None
    except Exception as e:
        logger.error(f"Error fetching single transaction {transaction_id}: {e}", exc_info=True)
        return None

def add_invoice(username, branch, invoice_data):
    db = current_app.db
    if db is None: return False
    try:
        doc = {
            'username': username, 'branch': branch, 'folder_name': invoice_data.get('folder_name'),
            'category': invoice_data.get('category'), 'invoice_date': invoice_data.get('invoice_date'),
            'original_filename': invoice_data.get('original_filename'),
            'saved_filename': invoice_data.get('saved_filename'), 'filepath': invoice_data.get('filepath'),
            'filesize': invoice_data.get('filesize'), 'createdAt': datetime.now(pytz.utc)
        }
        db.invoices.insert_one(doc)
        logger.info(f"Invoice '{doc['original_filename']}' added successfully for user '{username}'.")
        return True
    except Exception as e:
        logger.error(f"Error adding invoice for user {username}: {e}", exc_info=True)
        return False

def get_invoices(username, branch):
    db = current_app.db
    if db is None: return []
    try:
        query = {'username': username, 'branch': branch}
        invoices = list(db.invoices.find(query).sort('createdAt', -1))
        return invoices
    except Exception as e:
        logger.error(f"Error fetching invoices for {username} in {branch}: {e}", exc_info=True)
        return []


# PWA Notification and Subscription model functions
def add_notification(username, title, message, url=None):
    db = current_app.db
    if not db: return False
    try:
        notification = {
            'username': username, 'title': title, 'message': message, 'url': url,
            'is_read': False, 'createdAt': datetime.now(pytz.utc)
        }
        db.notifications.insert_one(notification)
        return True
    except Exception as e:
        logger.error(f"Error adding notification for {username}: {e}", exc_info=True)
        return False

def get_unread_notifications(username):
    db = current_app.db
    if not db: return []
    try:
        notifications = list(db.notifications.find({'username': username, 'is_read': False}).sort('createdAt', -1))
        for n in notifications:
            n['_id'] = str(n['_id'])
            n['createdAt'] = n['createdAt'].isoformat()
        return notifications
    except Exception as e:
        logger.error(f"Error fetching notifications for {username}: {e}", exc_info=True)
        return []

def mark_notifications_as_read(username):
    db = current_app.db
    if not db: return False
    try:
        db.notifications.update_many({'username': username, 'is_read': False}, {'$set': {'is_read': True}})
        return True
    except Exception as e:
        logger.error(f"Error marking notifications as read for {username}: {e}", exc_info=True)
        return False

def save_push_subscription(username, subscription_info):
    db = current_app.db
    if not db: return False
    try:
        db.users.update_one(
            {'username': username},
            {'$addToSet': {'push_subscriptions': subscription_info}}
        )
        logger.info(f"Saved push subscription for user '{username}'.")
        return True
    except Exception as e:
        logger.error(f"Error saving push subscription for {username}: {e}", exc_info=True)
        return False