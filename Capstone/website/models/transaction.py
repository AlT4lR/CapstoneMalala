# website/models/transaction.py

import logging
from datetime import datetime
import pytz
from bson.objectid import ObjectId
from flask import current_app

logger = logging.getLogger(__name__)

# =========================================================
# ADD TRANSACTION (UPDATED FOR MANUAL COUNTERED CHECK)
# =========================================================
def add_transaction(username, branch, transaction_data, parent_id=None):
    db = current_app.db
    if db is None:
        return False
    try:
        check_date_obj = transaction_data.get('check_date')
        due_date_obj = transaction_data.get('due_date')
        
        doc = {
            'username': username,
            'branch': branch,
            'name': transaction_data.get('name_of_issued_check'),
            'check_no': transaction_data.get('check_no'),
            'check_date': pytz.utc.localize(datetime.combine(check_date_obj, datetime.min.time())) if check_date_obj else datetime.now(pytz.utc),
            'due_date': pytz.utc.localize(datetime.combine(due_date_obj, datetime.min.time())) if due_date_obj else None,
            'status': 'Pending',
            'createdAt': datetime.now(pytz.utc),
            'isArchived': False,
            'notes': transaction_data.get('notes', ''),
            'parent_id': ObjectId(parent_id) if parent_id else None
        }

        if parent_id is None: # This is a FOLDER
            doc['amount'] = float(transaction_data.get('amount') or 0.0)
        else: # This is a CHILD CHECK
            check_amount = float(transaction_data.get('check_amount') or 0.0)
            deductions = transaction_data.get('deductions', [])
            countered_check = float(transaction_data.get('countered_check') or 0.0)
            
            # --- START OF CHANGE: Handle EWT separately ---
            ewt = float(transaction_data.get('ewt') or 0.0)
            doc['ewt'] = ewt
            # --- END OF CHANGE ---
            
            doc['countered_check'] = countered_check
            doc['check_amount'] = check_amount
            doc['deductions'] = deductions
            doc['amount'] = countered_check 

        db.transactions.insert_one(doc)
        return True
    except Exception as e:
        logger.error(f"Error adding transaction: {e}", exc_info=True)
        return False

# =========================================================
# UPDATE CHILD TRANSACTION (UPDATED FOR MANUAL COUNTERED CHECK)
# =========================================================
def update_child_transaction(username, transaction_id, form_data):
    db = current_app.db
    if db is None:
        return False
    try:
        check_amount = float(form_data.get('check_amount') or 0.0)
        deductions = form_data.get('deductions', []) 
        countered_check = float(form_data.get('countered_check') or 0.0)
        
        # --- START OF CHANGE: Handle EWT separately ---
        ewt = float(form_data.get('ewt') or 0.0)
        # --- END OF CHANGE ---
        
        update_fields = {
            'name': form_data.get('name_of_issued_check'),
            'check_no': form_data.get('check_no'),
            'notes': form_data.get('notes'),
            'check_amount': check_amount,
            'deductions': deductions,
            'countered_check': countered_check,
            'amount': countered_check,
            'ewt': ewt # Set EWT from its own field
        }
        
        check_date_obj = form_data.get('check_date')
        if check_date_obj:
            update_fields['check_date'] = pytz.utc.localize(datetime.combine(check_date_obj, datetime.min.time()))

        result = db.transactions.update_one(
            {'_id': ObjectId(transaction_id), 'username': username},
            {'$set': update_fields}
        )
        return result.modified_count == 1
    except Exception as e:
        logger.error(f"Error updating child transaction {transaction_id}: {e}", exc_info=True)
        return False

# (The other functions in this file are unchanged)
def get_transaction_by_id(username, transaction_id, full_document=False):
    db = current_app.db
    if db is None: return None
    try:
        doc = db.transactions.find_one({'_id': ObjectId(transaction_id), 'username': username})
        if not doc: return None
        if full_document: return doc
        check_date_str = doc.get('check_date').strftime('%Y-%m-%d') if isinstance(doc.get('check_date'), datetime) else ''
        due_date_str = doc.get('due_date').strftime('%Y-%m-%d') if isinstance(doc.get('due_date'), datetime) else ''
        return {'_id': str(doc['_id']), 'name': doc.get('name'), 'check_no': doc.get('check_no'), 'check_date': check_date_str, 'due_date': due_date_str, 'check_amount': doc.get('check_amount', 0.0), 'deductions': doc.get('deductions', []), 'countered_check': doc.get('countered_check', 0.0), 'amount': doc.get('amount', 0.0), 'notes': doc.get('notes', ''), 'status': doc.get('status'), 'ewt': doc.get('ewt', 0.0)}
    except Exception as e:
        logger.error(f"CRITICAL ERROR fetching transaction {transaction_id}: {e}", exc_info=True)
        return None
def get_transactions_by_status(username, branch, status):
    db = current_app.db
    if db is None: return []
    transactions = []
    try:
        query = {'username': username, 'status': status, 'parent_id': None, '$or': [{'isArchived': {'$exists': False}}, {'isArchived': False}]}
        if branch: query['branch'] = branch
        for doc in db.transactions.find(query).sort('check_date', -1):
            editor = (doc.get('paidBy', doc.get('username', 'N/A')).capitalize() if status == 'Paid' else doc.get('username', 'N/A').capitalize())
            check_date_str = doc.get('check_date').strftime('%m/%d/%Y') if isinstance(doc.get('check_date'), datetime) else 'N/A'
            due_date_str = doc.get('due_date').strftime('%m/%d/%Y') if isinstance(doc.get('due_date'), datetime) else 'N/A'
            transactions.append({'_id': str(doc['_id']), 'name': doc.get('name'), 'check_date': check_date_str, 'due_date': due_date_str, 'editor': editor})
    except Exception as e:
        logger.error(f"Error fetching transactions: {e}", exc_info=True)
    return transactions
def get_child_transactions_by_parent_id(username, parent_id):
    db = current_app.db
    if db is None: return []
    child_checks = []
    try:
        for doc in db.transactions.find({'username': username, 'parent_id': ObjectId(parent_id), '$or': [{'isArchived': {'$exists': False}}, {'isArchived': False}]}).sort('createdAt', 1):
            child_checks.append(doc)
    except Exception as e:
        logger.error(f"Error fetching child transactions for parent {parent_id}: {e}", exc_info=True)
    return child_checks
def update_transaction(username, transaction_id, form_data):
    db = current_app.db
    if db is None: return False
    try:
        update_fields = {'name': form_data.get('name'), 'notes': form_data.get('notes')}
        try: update_fields['amount'] = float(form_data.get('amount') or 0.0)
        except (ValueError, TypeError): update_fields['amount'] = 0.0
        if form_data.get('check_date'): update_fields['check_date'] = pytz.utc.localize(datetime.combine(form_data.get('check_date'), datetime.min.time()))
        if form_data.get('due_date'): update_fields['due_date'] = pytz.utc.localize(datetime.combine(form_data.get('due_date'), datetime.min.time()))
        else: update_fields['due_date'] = None
        result = db.transactions.update_one({'_id': ObjectId(transaction_id), 'username': username}, {'$set': update_fields})
        return result.modified_count == 1
    except Exception as e:
        logger.error(f"Error updating transaction {transaction_id}: {e}", exc_info=True)
        return False
def mark_folder_as_paid(username, folder_id, notes):
    db = current_app.db
    if db is None: return False
    try:
        paid_at_time = datetime.now(pytz.utc)
        update_data = {'$set': {'status': 'Paid', 'paidAt': paid_at_time, 'paidBy': username}}
        if notes is not None: update_data['$set']['notes'] = notes
        result = db.transactions.update_one({'_id': ObjectId(folder_id), 'username': username}, update_data)
        if result.modified_count == 0: return False
        db.transactions.update_many({'parent_id': ObjectId(folder_id), 'username': username}, {'$set': {'status': 'Paid', 'paidAt': paid_at_time}})
        return True
    except Exception as e:
        logger.error(f"Error marking folder {folder_id} as paid: {e}", exc_info=True)
        return False
def archive_transaction(username, transaction_id):
    db = current_app.db
    if db is None: return False
    try:
        result = db.transactions.update_one({'_id': ObjectId(transaction_id), 'username': username}, {'$set': {'isArchived': True, 'archivedAt': datetime.now(pytz.utc)}})
        return result.modified_count == 1
    except Exception as e:
        logger.error(f"Error archiving transaction {transaction_id}: {e}", exc_info=True)
        return False