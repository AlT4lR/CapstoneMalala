# website/models.py

import bcrypt
from pymongo.errors import DuplicateKeyError
import logging
from datetime import datetime, timedelta, date
import pytz
from flask import current_app, url_for
import pyotp
import re
from bson.objectid import ObjectId
from calendar import month_name
import random
import string
from .constants import LOGIN_ATTEMPT_LIMIT, LOCKOUT_DURATION_MINUTES

logger = logging.getLogger(__name__)

# =========================================================
# --- Helper Function ---
# =========================================================
def _format_relative_time(dt):
    """Formats a datetime object into a relative time string."""
    if not dt: return 'N/A'
    if dt.tzinfo is None:
        dt = pytz.utc.localize(dt)
    now = datetime.now(pytz.utc)
    diff = now - dt
    seconds = diff.total_seconds()
    if seconds < 60: return "just now"
    minutes = seconds / 60
    if minutes < 60: return f"{int(minutes)}m ago"
    hours = minutes / 60
    if hours < 24: return f"{int(hours)}h ago"
    days = hours / 24
    if days < 7: return f"{int(days)}d ago"
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
            'notes': '',
            'push_subscriptions': []
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

def save_push_subscription(username, subscription_info):
    db = current_app.db
    if db is None: return False
    try:
        db.users.update_one({'username': username}, {'$addToSet': {'push_subscriptions': subscription_info}})
        return True
    except Exception as e:
        logger.error(f"Error saving push subscription for {username}: {e}", exc_info=True)
        return False

def get_user_push_subscriptions(username):
    db = current_app.db
    if db is None: return []
    user = get_user_by_username(username)
    return user.get('push_subscriptions', []) if user else []


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

def get_recent_activity(username, limit=10):
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
        logger.error(f"Error fetching recent activity for {username}: {e}", exc_info=True)
    return activities


# =========================================================
# --- Invoice Models ---
# =========================================================
def add_invoice(username, branch, invoice_data, files, extracted_text):
    db = current_app.db
    if db is None: return False
    try:
        db.invoices.insert_one({
            'username': username,
            'branch': branch,
            'folder_name': invoice_data.get('folder_name'),
            'category': invoice_data.get('category'),
            'date': invoice_data.get('date'),
            'files': files,
            'extracted_text': extracted_text,
            'createdAt': datetime.now(pytz.utc),
            'isArchived': False
        })
        return True
    except Exception as e:
        logger.error(f"Error adding invoice for {username}: {e}", exc_info=True)
        return False

def get_invoices(username, branch):
    db = current_app.db
    if db is None: return []
    invoices = []
    try:
        query = {
            'username': username,
            'branch': branch,
            '$or': [{'isArchived': {'$exists': False}}, {'isArchived': False}]
        }
        for doc in db.invoices.find(query).sort('date', -1):
            invoices.append({
                'id': str(doc['_id']),
                'file_name': doc.get('folder_name', 'N/A'),
                'date': doc.get('date').strftime('%m/%d/%Y') if doc.get('date') else 'N/A',
                'category': doc.get('category', 'N/A')
            })
    except Exception as e:
        logger.error(f"Error fetching invoices for {username}: {e}", exc_info=True)
    return invoices

def get_invoice_by_id(username, invoice_id):
    db = current_app.db
    if db is None: return None
    try:
        query = {'_id': ObjectId(invoice_id), 'username': username}
        invoice = db.invoices.find_one(query)
        if invoice:
            invoice['_id'] = str(invoice['_id'])
        return invoice
    except Exception as e:
        logger.error(f"Error fetching invoice {invoice_id}: {e}", exc_info=True)
        return None

def archive_invoice(username, invoice_id):
    db = current_app.db
    if db is None: return False
    try:
        result = db.invoices.update_one(
            {'_id': ObjectId(invoice_id), 'username': username},
            {'$set': {'isArchived': True, 'archivedAt': datetime.now(pytz.utc)}}
        )
        return result.modified_count == 1
    except Exception as e:
        logger.error(f"Error archiving invoice {invoice_id}: {e}", exc_info=True)
        return False


# =========================================================
# --- Transaction Models ---
# =========================================================
def add_transaction(username, branch, transaction_data, parent_id=None):
    db = current_app.db
    if db is None: return False
    try:
        check_date_obj = transaction_data.get('check_date')
        countered_check_val = transaction_data.get('countered_check')
        ewt_val = transaction_data.get('ewt')

        doc = {
            'username': username, 'branch': branch,
            'name': transaction_data.get('name_of_issued_check'),
            'check_no': transaction_data.get('check_no'),
            'check_date': pytz.utc.localize(datetime.combine(check_date_obj, datetime.min.time())) if check_date_obj else datetime.now(pytz.utc),
            'countered_check': float(countered_check_val or 0.0),
            'amount': float(countered_check_val or 0.0),
            'ewt': float(ewt_val or 0.0),
            'status': 'Pending',
            'createdAt': datetime.now(pytz.utc),
            'isArchived': False,
            'notes': '',
            'parent_id': ObjectId(parent_id) if parent_id else None
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
            'parent_id': None,
            '$or': [{'isArchived': {'$exists': False}}, {'isArchived': False}]
        }
        if branch: query['branch'] = branch

        for doc in db.transactions.find(query).sort('check_date', -1):
            editor = doc.get('paidBy', doc.get('username', 'N/A')).capitalize() if status == 'Paid' else doc.get('username', 'N/A').capitalize()
            transaction_info = {
                '_id': str(doc['_id']),
                'name': doc.get('name'),
                'check_date': doc.get('check_date').strftime('%m/%d/%Y') if doc.get('check_date') else 'N/A',
                'editor': editor
            }
            transactions.append(transaction_info)
    except Exception as e:
        logger.error(f"Error fetching transactions: {e}", exc_info=True)
    return transactions


def get_child_transactions_by_parent_id(username, parent_id):
    db = current_app.db
    if db is None: return []
    child_checks = []
    try:
        query = {
            'username': username,
            'parent_id': ObjectId(parent_id),
            'status': 'Pending',
            '$or': [{'isArchived': {'$exists': False}}, {'isArchived': False}]
        }
        for doc in db.transactions.find(query).sort('createdAt', 1):
            child_checks.append(doc)
    except Exception as e:
        logger.error(f"Error fetching child transactions for parent {parent_id}: {e}", exc_info=True)
    return child_checks


def get_transaction_by_id(username, transaction_id, full_document=False):
    db = current_app.db
    if db is None: return None
    try:
        doc = db.transactions.find_one({'_id': ObjectId(transaction_id), 'username': username})
        if not doc: return None
        if full_document: return doc

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


def update_transaction(username, transaction_id, form_data):
    """Updates an existing transaction in the database."""
    db = current_app.db
    if db is None: return False
    try:
        update_fields = {
            'name': form_data.get('name'),
            'notes': form_data.get('notes')
        }
        for field in ['ewt', 'countered_check']:
            value = form_data.get(field)
            try:
                update_fields[field] = float(value) if value is not None else 0.0
            except (ValueError, TypeError):
                update_fields[field] = 0.0
        
        check_date_obj = form_data.get('check_date')
        if check_date_obj:
            update_fields['check_date'] = pytz.utc.localize(datetime.combine(check_date_obj, datetime.min.time()))

        result = db.transactions.update_one(
            {'_id': ObjectId(transaction_id), 'username': username},
            {'$set': update_fields}
        )
        return result.modified_count == 1
    except Exception as e:
        logger.error(f"Error updating transaction {transaction_id}: {e}", exc_info=True)
        return False


def mark_folder_as_paid(username, folder_id, notes, amount):
    db = current_app.db
    if db is None: return False
    try:
        update_data = {
            '$set': {
                'status': 'Paid',
                'amount': float(amount),
                'paidAt': datetime.now(pytz.utc),
                'paidBy': username
            }
        }
        if notes is not None:
            update_data['$set']['notes'] = notes
        result = db.transactions.update_one({'_id': ObjectId(folder_id), 'username': username}, update_data)
        if result.modified_count == 0:
            logger.warning(f"No document found or updated for folder {folder_id} for user {username}.")
            return False
        db.transactions.update_many({'parent_id': ObjectId(folder_id), 'username': username}, {'$set': {'status': 'Paid'}})
        return True
    except Exception as e:
        logger.error(f"Error marking folder {folder_id} as paid: {e}", exc_info=True)
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


# =========================================================
# --- Loan Models ---
# =========================================================
def add_loan(username, branch, loan_data):
    db = current_app.db
    if db is None: return False
    try:
        date_issued_obj = loan_data.get('date_issued')
        date_paid_obj = loan_data.get('date_paid')
        doc = {
            'username': username,
            'branch': branch,
            'name': loan_data.get('name_of_loan'),
            'bank_name': loan_data.get('bank_name'),
            'amount': float(loan_data.get('amount', 0.0)),
            'date_issued': pytz.utc.localize(datetime.combine(date_issued_obj, datetime.min.time())) if date_issued_obj else None,
            'date_paid': pytz.utc.localize(datetime.combine(date_paid_obj, datetime.min.time())) if date_paid_obj else None,
            'createdAt': datetime.now(pytz.utc),
            'isArchived': False
        }
        db.loans.insert_one(doc)
        return True
    except Exception as e:
        logger.error(f"Error adding loan for {username}: {e}", exc_info=True)
        return False


def get_loans(username, branch):
    """Fetches a list of non-archived loans for a user and branch."""
    db = current_app.db
    if db is None: return []
    loans_list = []
    try:
        query = {
            'username': username,
            'branch': branch,
            '$or': [{'isArchived': {'$exists': False}}, {'isArchived': False}]
        }
        for doc in db.loans.find(query).sort('date_issued', -1):
            loans_list.append({
                'id': str(doc['_id']),
                'name': doc.get('name', 'N/A'),
                'bank_name': doc.get('bank_name', 'N/A'),
                'amount': doc.get('amount', 0.0),
                'date_issued': doc.get('date_issued'),
                'date_paid': doc.get('date_paid')
            })
    except Exception as e:
        logger.error(f"Error fetching loans for {username}: {e}", exc_info=True)
    return loans_list


# =========================================================
# --- Schedule Models ---
# =========================================================
def add_schedule(username, schedule_data):
    db = current_app.db
    if db is None: return False
    try:
        is_all_day = 'all_day' in schedule_data and schedule_data['all_day'] == 'on'
        date_str = schedule_data.get('date')

        if is_all_day:
            start_dt = datetime.strptime(date_str, '%Y-%m-%d')
            end_dt = start_dt + timedelta(days=1)
        else:
            start_time_str = schedule_data.get('start_time') or '00:00'
            end_time_str = schedule_data.get('end_time')
            start_dt = datetime.strptime(f"{date_str}T{start_time_str}", '%Y-%m-%dT%H:%M')
            if end_time_str:
                end_dt = datetime.strptime(f"{date_str}T{end_time_str}", '%Y-%m-%dT%H:%M')
            else:
                end_dt = start_dt + timedelta(hours=1)
        
        db.schedules.insert_one({
            'username': username,
            'title': schedule_data.get('title'),
            'description': schedule_data.get('description'),
            'location': schedule_data.get('location'),
            'start': start_dt.replace(tzinfo=pytz.utc),
            'end': end_dt.replace(tzinfo=pytz.utc),
            'allDay': is_all_day,
            'createdAt': datetime.now(pytz.utc)
        })
        return True
    except Exception as e:
        logger.error(f"Error adding schedule for {username}: {e}", exc_info=True)
        return False


def get_schedules(username, branch, start_str, end_str):
    db = current_app.db
    if db is None: return []
    schedules = []
    try:
        start_date = datetime.fromisoformat(start_str.replace('Z', '+00:00'))
        end_date = datetime.fromisoformat(end_str.replace('Z', '+00:00'))
        query = {
            'username': username,
            'branch': branch,
            'start': {'$lt': end_date},
            'end': {'$gte': start_date}
        }
        for doc in db.schedules.find(query):
            schedules.append({
                'id': str(doc['_id']),
                'title': doc.get('title'),
                'start': doc.get('start').isoformat(),
                'end': doc.get('end').isoformat(),
                'allDay': doc.get('allDay'),
                'description': doc.get('description'),
                'location': doc.get('location')
            })
    except Exception as e:
        logger.error(f"Error fetching schedules for {username}: {e}", exc_info=True)
    return schedules


def update_schedule(username, schedule_id, data):
    db = current_app.db
    if db is None: return False
    try:
        update_fields = {}
        if 'start' in data and data['start']:
            update_fields['start'] = datetime.fromisoformat(data['start'].replace('Z', '+00:00'))
        if 'end' in data and data['end']:
            update_fields['end'] = datetime.fromisoformat(data['end'].replace('Z', '+00:00'))
        if 'allDay' in data:
            update_fields['allDay'] = data['allDay']
        if 'title' in data:
            update_fields['title'] = data['title']
        if 'description' in data:
            update_fields['description'] = data['description']
        if 'location' in data:
            update_fields['location'] = data['location']
        
        result = db.schedules.update_one(
            {'_id': ObjectId(schedule_id), 'username': username},
            {'$set': update_fields}
        )
        return result.modified_count > 0
    except Exception as e:
        logger.error(f"Error updating schedule {schedule_id}: {e}", exc_info=True)
        return False


def delete_schedule(username, schedule_id):
    db = current_app.db
    if db is None: return False
    try:
        result = db.schedules.delete_one({'_id': ObjectId(schedule_id), 'username': username})
        return result.deleted_count > 0
    except Exception as e:
        logger.error(f"Error deleting schedule {schedule_id}: {e}", exc_info=True)
        return False


# =========================================================
# --- Restore / Permanent Delete Models ---
# =========================================================
def restore_item(username, item_type, item_id):
    db = current_app.db
    if db is None: return False
    collection_name = f"{item_type.lower()}s" 
    if collection_name not in db.list_collection_names():
        return False
    try:
        result = db[collection_name].update_one(
            {'_id': ObjectId(item_id), 'username': username},
            {'$set': {'isArchived': False}, '$unset': {'archivedAt': ''}}
        )
        return result.modified_count == 1
    except Exception as e:
        logger.error(f"Error restoring {item_type} {item_id}: {e}", exc_info=True)
        return False


def delete_item_permanently(username, item_type, item_id):
    db = current_app.db
    if db is None: return False
    collection_name = f"{item_type.lower()}s"
    if collection_name not in db.list_collection_names():
        return False
    try:
        result = db[collection_name].delete_one({'_id': ObjectId(item_id), 'username': username})
        return result.deleted_count == 1
    except Exception as e:
        logger.error(f"Error permanently deleting {item_type} {item_id}: {e}", exc_info=True)
        return False


def get_archived_items(username):
    db = current_app.db
    if db is None: return []
    items = []
    collections_to_check = ['transactions', 'invoices']
    for collection_name in collections_to_check:
        try:
            for doc in db[collection_name].find({'username': username, 'isArchived': True}):
                items.append({
                    'id': str(doc['_id']),
                    'name': doc.get('name') or doc.get('folder_name', 'Archived Item'),
                    'type': collection_name.rstrip('s').capitalize(),
                    'details': f"Archived on {doc.get('archivedAt', datetime.now(pytz.utc)).strftime('%Y-%m-%d')}",
                    'archived_at_str': doc.get('archivedAt').strftime('%b %d, %Y') if doc.get('archivedAt') else 'N/A',
                    'relative_time': _format_relative_time(doc.get('archivedAt')) if doc.get('archivedAt') else 'N/A'
                })
        except Exception as e:
            logger.error(f"Error fetching archived items from {collection_name} for {username}: {e}")
    items.sort(key=lambda x: x['relative_time'], reverse=True)
    return items

# =========================================================
# --- Analytics / Dashboard Data ---
# =========================================================
def get_analytics_data(username, branch, year, month):
    db = current_app.db
    if db is None: return {}

    try:
        year_start = datetime(year, 1, 1, tzinfo=pytz.utc)
        year_end = datetime(year + 1, 1, 1, tzinfo=pytz.utc)
        month_start = datetime(year, month, 1, tzinfo=pytz.utc)
        next_month_val = month + 1 if month < 12 else 1
        next_year_val = year if month < 12 else year + 1
        month_end = datetime(next_year_val, next_month_val, 1, tzinfo=pytz.utc)

        year_pipeline = [
            {'$match': {'username': username, 'branch': branch, 'status': 'Paid', 'paidAt': {'$gte': year_start, '$lt': year_end}}},
            {'$group': {'_id': None, 'total': {'$sum': '$amount'}}}
        ]
        year_result = list(db.transactions.aggregate(year_pipeline))
        total_year_earning = year_result[0]['total'] if year_result else 0.0

        month_pipeline = [
            {'$match': {'username': username, 'branch': branch, 'status': 'Paid', 'paidAt': {'$gte': year_start, '$lt': year_end}}},
            {'$group': {'_id': {'$month': '$paidAt'}, 'total': {'$sum': '$amount'}}}
        ]
        monthly_totals_docs = list(db.transactions.aggregate(month_pipeline))
        monthly_totals = {doc['_id']: doc['total'] for doc in monthly_totals_docs}
        max_earning = max(monthly_totals.values()) if monthly_totals else 0

        chart_data = []
        for i in range(1, 13):
            total = monthly_totals.get(i, 0.0)
            percentage = (total / max_earning * 100) if max_earning > 0 else 0
            chart_data.append({
                'month_name': month_name[i][:3].upper(),
                'total': total,
                'percentage': percentage,
                'is_current_month': i == month
            })

        weekly_pipeline = [
            {'$match': {'username': username, 'branch': branch, 'status': 'Paid', 'paidAt': {'$gte': month_start, '$lt': month_end}}},
            {'$group': {'_id': {'$week': '$paidAt'}, 'total': {'$sum': '$amount'}}},
            {'$sort': {'_id': 1}}
        ]
        weekly_docs = list(db.transactions.aggregate(weekly_pipeline))
        weekly_breakdown = [{'week': f"Week {i + 1}", 'total': doc['total']} for i, doc in enumerate(weekly_docs)]
        
        current_month_total = monthly_totals.get(month, 0.0)

        return {
            'year': year,
            'total_year_earning': total_year_earning,
            'current_month_name': month_name[month],
            'current_month_total': current_month_total,
            'chart_data': chart_data,
            'weekly_breakdown': weekly_breakdown,
        }
    except Exception as e:
        logger.error(f"Error getting analytics data for {username}: {e}", exc_info=True)
        return {}


# =========================================================
# --- Weekly Billing Summary ---
# =========================================================
def get_weekly_billing_summary(username, year, week):
    db = current_app.db
    if db is None: return {}
    try:
        start_of_week = datetime.fromisocalendar(year, week, 1).replace(tzinfo=pytz.utc)
        end_of_week = start_of_week + timedelta(days=7)

        paid_tx_pipeline = [
            {'$match': {
                'username': username,
                'status': 'Paid',
                'paidAt': {'$gte': start_of_week, '$lt': end_of_week}
            }},
            {'$group': {
                '_id': None,
                'total_check_amount': {'$sum': '$amount'},
                'total_ewt': {'$sum': '$ewt'},
                'total_countered': {'$sum': '$countered_check'}
            }}
        ]
        paid_tx_result = list(db.transactions.aggregate(paid_tx_pipeline))
        
        loans_pipeline = [
            {'$match': {
                'username': username,
                'date_paid': {'$gte': start_of_week, '$lt': end_of_week}
            }},
            {'$group': {
                '_id': None,
                'total_loans': {'$sum': '$amount'}
            }}
        ]
        loans_result = list(db.loans.aggregate(loans_pipeline))

        summary = {
            'check_amount': paid_tx_result[0]['total_check_amount'] if paid_tx_result else 0,
            'ewt_collected': paid_tx_result[0]['total_ewt'] if paid_tx_result else 0,
            'countered_check': paid_tx_result[0]['total_countered'] if paid_tx_result else 0,
            'other_loans': loans_result[0]['total_loans'] if loans_result else 0
        }
        return summary
    except Exception as e:
        logger.error(f"Error generating weekly billing summary for {username}: {e}", exc_info=True)
        return {}


# =========================================================
# --- Notifications ---
# =========================================================
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
            'relative_time': _format_relative_time(n['createdAt'])
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