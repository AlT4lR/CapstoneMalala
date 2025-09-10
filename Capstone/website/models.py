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

def add_user(username, email, password):
    db = current_app.db
    if db is None:
        logger.error("Database not available.")
        return False

    hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
    otp_secret = pyotp.random_base32()

    user_data = {
        'username': username.strip().lower(),
        'email': email.strip().lower(),
        'passwordHash': hashed_password,
        'role': 'user',
        'isActive': False,
        'otp': None,
        'otpExpiresAt': None,
        'otpSecret': otp_secret,
        'failedLoginAttempts': 0,
        'lockoutUntil': None,
        'lastLogin': None,
        'createdAt': datetime.now(pytz.utc),
        'updatedAt': datetime.now(pytz.utc)
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
            {'$set': {
                'lastLogin': datetime.now(pytz.utc),
                'failedLoginAttempts': 0,
                'lockoutUntil': None,
                'updatedAt': datetime.now(pytz.utc)
            }}
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

# --- Schedule Operations ---
def add_schedule(username, title, start_time, end_time, category, notes=None):
    db = current_app.db
    if db is None: return False
    schedule_data = {
        'username': username,
        'title': title.strip(),
        'start_time': start_time,
        'end_time': end_time,
        'category': category.strip(),
        'notes': notes.strip() if notes else None,
        'createdAt': datetime.now(pytz.utc),
        'updatedAt': datetime.now(pytz.utc)
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

# --- Category Operations ---
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
def add_transaction(username, branch, transaction_data):
    db = current_app.db
    if db is None:
        logger.error("Database not available. Cannot add transaction.")
        return False
    try:
        doc = {
            'username': username,
            'branch': branch,
            'transaction_id': transaction_data.get('transaction_id'),
            'name': transaction_data.get('name'),
            'datetime_utc': transaction_data.get('datetime_utc'),
            'amount': float(transaction_data.get('amount')),
            'method': transaction_data.get('payment_method'),
            'status': transaction_data.get('status'),
            'notes': transaction_data.get('notes', 'Added via form.'),
            'createdAt': datetime.now(pytz.utc),
            'updatedAt': datetime.now(pytz.utc)
        }
        db.transactions.insert_one(doc)
        logger.info(f"Transaction added successfully for user '{username}'.")
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
        for doc in db.transactions.find(query).sort('datetime_utc', -1):
            dt = doc.get('datetime_utc')
            transactions.append({
                'id': doc.get('transaction_id'),
                'name': doc.get('name'),
                'date': dt.strftime('%Y-%m-%d') if dt else '',
                'time': dt.strftime('%I:%M %p') if dt else '',
                'amount': doc.get('amount'),
                'method': doc.get('method'),
                'status': doc.get('status'),
                'notes': doc.get('notes'),
                'branch': doc.get('branch')
            })
    except Exception as e:
        logger.error(f"Error fetching transactions for {username}: {e}", exc_info=True)
    return transactions
