# website/models.py

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
# ... (all existing user functions remain here) ...
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
def add_user(username, email, password):
    db = current_app.db
    if db is None:
        logger.error("Database not available.")
        return False
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
        if user.get('otp') == submitted_otp and otp_expires_at > datetime.now(pytz.utc):
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
        if not otp_secret: return False
        totp = pyotp.TOTP(otp_secret)
        return totp.verify(submitted_otp, valid_window=1)
    return False

# --- Schedule & Category Operations ---
# ... (all existing schedule/category functions remain here) ...
def add_schedule(username, title, start_time, end_time, category, notes=None):
    db = current_app.db
    if db is None: return False
    schedule_data = {
        'username': username, 'title': title.strip(), 'start_time': start_time, 'end_time': end_time,
        'category': category.strip(), 'notes': notes.strip() if notes else None,
        'createdAt': datetime.now(pytz.utc), 'updatedAt': datetime.now(pytz.utc)
    }
    try:
        db.schedules.insert_one(schedule_data)
        return True
    except Exception as e:
        logger.error(f"Error adding schedule for {username}: {e}")
        return False
def get_schedules_by_date_range(username, start_date, end_date):
    db = current_app.db
    if db is None: return []
    query = {'username': username, 'start_time': {'$gte': start_date, '$lt': end_date}}
    schedules = []
    try:
        for doc in db.schedules.find(query).sort('start_time', 1):
            doc['_id'] = str(doc['_id'])
            doc['start_time'] = doc['start_time'].isoformat()
            doc['end_time'] = doc['end_time'].isoformat()
            schedules.append(doc)
    except Exception as e:
        logger.error(f"Error fetching schedules for {username}: {e}")
    return schedules
def get_all_categories(username):
    db = current_app.db
    if db is None: return DEFAULT_SCHEDULE_CATEGORIES
    try:
        categories = db.schedules.distinct('category', {'username': username})
        return categories if categories else DEFAULT_SCHEDULE_CATEGORIES
    except Exception as e:
        logger.error(f"Error fetching categories for {username}: {e}")
        return DEFAULT_SCHEDULE_CATEGORIES
def add_category(username, category_name):
    logger.info(f"Conceptual: Category '{category_name}' added for user '{username}'.")
    return True

# --- Transaction Operations ---
# --- THIS IS THE FIX ---
# Added 'payment_method' to the document being saved.
def add_transaction(username, branch, transaction_data):
    db = current_app.db
    if db is None:
        logger.error("Database not available. Cannot add transaction.")
        return False
    try:
        check_date_obj = transaction_data.get('check_date')
        datetime_utc = pytz.utc.localize(datetime.combine(check_date_obj, datetime.min.time())) if check_date_obj else datetime.now(pytz.utc)

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
            'notes': transaction_data.get('notes', ''), # Default to empty string
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
    if db is None:
        logger.error("Database not available. Cannot delete transaction.")
        return False
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

# --- THIS IS THE FIX ---
# The API function now retrieves and returns the 'method' field for the modal.
def get_transaction_by_id(username, transaction_id):
    db = current_app.db
    if db is None: return None
    try:
        doc = db.transactions.find_one({
            '_id': ObjectId(transaction_id),
            'username': username
        })
        if doc:
            dt = doc.get('check_date')
            return {
                '_id': str(doc.get('_id')),
                'id': doc.get('check_no'),
                'name': doc.get('name'),
                'delivery_date_full': dt.strftime('%m/%d/%Y %I:%M %p') if dt else 'N/A',
                'check_date_only': dt.strftime('%m/%d/%Y') if dt else 'N/A',
                'amount': doc.get('amount'),
                'method': doc.get('method', 'N/A'),
                'status': doc.get('status'),
                'notes': doc.get('notes', 'No notes provided.')
            }
        return None
    except InvalidId:
        return None
    except Exception as e:
        logger.error(f"Error fetching single transaction {transaction_id}: {e}", exc_info=True)
        return None