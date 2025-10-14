# website/models.py

import bcrypt
from pymongo.errors import DuplicateKeyError
import logging
from datetime import datetime, timedelta
import pytz
from flask import current_app
import pyotp
import re
from bson.objectid import ObjectId
from calendar import month_name
import random
import string
from .constants import LOGIN_ATTEMPT_LIMIT, LOCKOUT_DURATION_MINUTES


logger = logging.getLogger(__name__)

# --- THIS IS THE FIX: Changed all `if db` checks to `if db is not None` ---

# --- User & Auth Models ---
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
            'username': username.strip().lower(), 'email': email.strip().lower(), 'passwordHash': hashed_password,
            'isActive': False, 'otpSecret': otp_secret, 'createdAt': datetime.now(pytz.utc),
            'failedLoginAttempts': 0, 'lockoutUntil': None, 'lastLogin': None
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
        lockout_time = datetime.utcnow() + timedelta(minutes=LOCKOUT_DURATION_MINUTES)
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

# --- Transaction & Other Models ---

def add_transaction(username, branch, transaction_data):
    db = current_app.db
    if db is None: return False
    try:
        check_date_obj = transaction_data.get('check_date')
        doc = {
            'username': username, 'branch': branch,
            'name': transaction_data.get('name_of_issued_check'),
            'check_no': transaction_data.get('check_no'),
            'check_date': pytz.utc.localize(datetime.combine(check_date_obj, datetime.min.time())) if check_date_obj else datetime.now(pytz.utc),
            'countered_check': float(transaction_data.get('countered_check', 0.0)),
            'amount': float(transaction_data.get('countered_check', 0.0)),
            'ewt': float(transaction_data.get('ewt', 0.0)),
            'status': 'Pending',
            'sub_branch': 'San Isidro',
            'createdAt': datetime.now(pytz.utc)
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
        for doc in db.transactions.find({'username': username, 'branch': branch, 'status': status}).sort('check_date', -1):
            transactions.append({
                '_id': str(doc['_id']), 'name': doc.get('name'), 'check_no': f"#{doc.get('check_no')}",
                'check_date': doc.get('check_date').strftime('%m/%d/%Y') if doc.get('check_date') else 'N/A',
                'ewt': f"₱ {doc.get('ewt', 0.0):,.2f}", 'countered_check': f"₱ {doc.get('countered_check', 0.0):,.2f}"
            })
    except Exception as e:
        logger.error(f"Error fetching transactions: {e}", exc_info=True)
    return transactions

def delete_transaction(username, transaction_id):
    db = current_app.db
    if db is None: return False
    try:
        result = db.transactions.delete_one({'_id': ObjectId(transaction_id), 'username': username})
        return result.deleted_count == 1
    except Exception as e:
        logger.error(f"Error deleting transaction {transaction_id}: {e}", exc_info=True)
        return False

def get_analytics_data(username, year):
    db = current_app.db
    if db is None: return {}
    # ... (rest of function is the same)
    pipeline_monthly = [
        {'$match': {'username': username, 'status': 'Paid', 'check_date': {'$gte': datetime(year, 1, 1, tzinfo=pytz.utc), '$lt': datetime(year + 1, 1, 1, tzinfo=pytz.utc)}}},
        {'$group': {'_id': {'$month': '$check_date'}, 'total': {'$sum': '$amount'}}}
    ]
    monthly_totals = {doc['_id']: doc['total'] for doc in db.transactions.aggregate(pipeline_monthly)}
    current_month = datetime.now().month
    pipeline_weekly = [
        {'$match': {'username': username, 'status': 'Paid', 'check_date': {'$gte': datetime(year, current_month, 1, tzinfo=pytz.utc), '$lt': datetime(year, current_month + 1, 1, tzinfo=pytz.utc) if current_month < 12 else datetime(year + 1, 1, 1, tzinfo=pytz.utc)}}},
        {'$group': {'_id': {'$week': '$check_date'}, 'total': {'$sum': '$amount'}}},
        {'$sort': {'_id': 1}}
    ]
    weekly_breakdown = [{'week': f"Week {i+1}", 'total': doc['total']} for i, doc in enumerate(db.transactions.aggregate(pipeline_weekly))]
    total_year_earning = sum(monthly_totals.values())
    max_monthly_earning = max(monthly_totals.values()) if monthly_totals else 1
    chart_data = [{'month_name': month_name[i][:3], 'total': monthly_totals.get(i, 0), 'percentage': (monthly_totals.get(i, 0) / max_monthly_earning) * 100 if max_monthly_earning > 0 else 0, 'is_current_month': i == current_month} for i in range(1, 13)]
    return {
        'year': year, 'total_year_earning': total_year_earning, 'chart_data': chart_data,
        'current_month_name': month_name[current_month].upper(), 'weekly_breakdown': weekly_breakdown,
        'current_month_total': monthly_totals.get(current_month, 0)
    }

# --- Placeholder functions required by __init__.py ---
def add_invoice(username, branch, invoice_data): return True
def get_transaction_by_id(username, transaction_id): return None
def add_notification(username, title, message, url): return True
def get_unread_notifications(username): return []
def mark_notifications_as_read(username): return True
def save_push_subscription(username, subscription_info): return True