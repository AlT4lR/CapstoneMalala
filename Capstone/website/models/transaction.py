# website/models/transaction.py

import logging
from datetime import datetime
import pytz
from bson import ObjectId
from bson.objectid import ObjectId
from flask import current_app

logger = logging.getLogger(__name__)


# --- START OF NEW FUNCTION: Recalculate Parent Folder Amount ---
def _recalculate_parent_folder_amount(db, parent_id, username):
    """
    Aggregates the 'amount' (which is 'countered_check') of all non-archived children
    and updates the parent folder's 'amount' field.
    """
    if not parent_id:
        return
    
    try:
        # Ensure parent_id is an ObjectId for the query
        parent_obj_id = ObjectId(parent_id)
        
        # Aggregate the sum of 'countered_check' from all non-archived children
        pipeline = [
            {'$match': {
                'parent_id': parent_obj_id,
                'username': username,
                '$or': [{'isArchived': {'$exists': False}}, {'isArchived': False}]
            }},
            {'$group': {
                '_id': '$parent_id',
                'new_parent_amount': {'$sum': '$countered_check'}
            }}
        ]
        
        # Execute the aggregation
        result = list(db.transactions.aggregate(pipeline))
        
        # Get the new total, defaulting to 0.0 if no children are found
        new_amount = result[0]['new_parent_amount'] if result else 0.0
        
        # Update the parent folder with the new aggregated amount
        db.transactions.update_one(
            {'_id': parent_obj_id, 'username': username},
            {'$set': {'amount': new_amount}}
        )
        
    except Exception as e:
        logger.error(f"Error recalculating parent amount for {parent_id}: {e}", exc_info=True)
# --- END OF NEW FUNCTION ---


# =========================================================
# UPDATE TRANSACTION (for Folders) - FIXED
# =========================================================
def update_transaction(username, transaction_id, form_data):
    """Updates an existing transaction FOLDER in the database."""
    db = current_app.db
    if db is None:
        return False
    try:
        # --- START OF FIX: Removed all logic related to the 'amount' field ---
        update_fields = {
            'name': form_data.get('name'),
            'notes': form_data.get('notes') 
        }
        
        check_date_str = form_data.get('check_date')
        if check_date_str:
            # FIX: Convert the string 'YYYY-MM-DD' to a datetime object before combining
            date_part = datetime.strptime(check_date_str, '%Y-%m-%d').date()
            update_fields['check_date'] = pytz.utc.localize(datetime.combine(date_part, datetime.min.time()))
        
        due_date_str = form_data.get('due_date')
        if due_date_str:
            # FIX: Convert the string 'YYYY-MM-DD' to a datetime object before combining
            date_part = datetime.strptime(due_date_str, '%Y-%m-%d').date()
            update_fields['due_date'] = pytz.utc.localize(datetime.combine(date_part, datetime.min.time()))
        else:
            # Explicitly set to None if the field is empty
            update_fields['$unset'] = {'due_date': ""}
        # --- END OF FIX ---

        set_updates = {k: v for k, v in update_fields.items() if k not in ['$unset', 'notes']}
        set_updates['notes'] = update_fields.get('notes', '')
        if 'notes' in update_fields:
            set_updates['notes'] = update_fields['notes']

        final_update = {}
        if set_updates:
            final_update['$set'] = set_updates
        if update_fields.get('$unset'):
            final_update['$unset'] = update_fields['$unset']

        result = db.transactions.update_one(
            {'_id': ObjectId(transaction_id), 'username': username},
            final_update
        )
        return result.modified_count == 1
    except Exception as e:
        logger.error(f"Error updating transaction {transaction_id}: {e}", exc_info=True)
        return False

# =========================================================
# ADD TRANSACTION (UPDATED LOGIC)
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
            # Amount is now derived from children, so we don't set it here initially.
            # We can initialize it to 0 for consistency.
            doc['amount'] = 0.0
            doc['check_amount'] = 0.0
            doc['countered_check'] = 0.0
            doc['ewt'] = 0.0
            doc['deductions'] = []
        else: # This is a CHILD CHECK (New Logic Applied)
            check_amount = float(transaction_data.get('check_amount') or 0.0)
            deductions = transaction_data.get('deductions', [])
            total_deductions = sum(d.get('amount', 0) for d in deductions)
            
            doc['check_amount'] = check_amount
            doc['deductions'] = deductions
            
            countered_check = check_amount - total_deductions
            doc['countered_check'] = countered_check
            doc['amount'] = countered_check
            
            doc['ewt'] = sum(d.get('amount', 0) for d in deductions if d.get('name', '').upper() == 'EWT')

        db.transactions.insert_one(doc)
        
        # --- START OF FIX: Recalculate parent folder amount on child creation ---
        if parent_id:
            _recalculate_parent_folder_amount(db, parent_id, username)
        # --- END OF FIX: Recalculate parent folder amount on child creation ---
        
        return True
    except Exception as e:
        logger.error(f"Error adding transaction: {e}", exc_info=True)
        return False

# =========================================================
# GET TRANSACTION BY ID
# =========================================================
def get_transaction_by_id(username, transaction_id, full_document=False):
    db = current_app.db
    if db is None:
        return None
    try:
        doc = db.transactions.find_one({'_id': ObjectId(transaction_id), 'username': username})
        if not doc:
            logger.warning(f"Transaction with id {transaction_id} not found for user {username}")
            return None
        if full_document:
            return doc

        check_date_str = ''
        check_date_val = doc.get('check_date')
        if isinstance(check_date_val, datetime):
            check_date_str = check_date_val.strftime('%Y-%m-%d')

        due_date_str = ''
        due_date_val = doc.get('due_date')
        if isinstance(due_date_val, datetime):
            due_date_str = due_date_val.strftime('%Y-%m-%d')

        return {
            '_id': str(doc['_id']),
            'name': doc.get('name'),
            'check_no': doc.get('check_no'),
            'check_date': check_date_str,
            'due_date': due_date_str,
            'check_amount': doc.get('check_amount', 0.0),
            'deductions': doc.get('deductions', []),
            'ewt': doc.get('ewt', 0.0),
            'countered_check': doc.get('countered_check', 0.0),
            'amount': doc.get('amount', 0.0),
            'notes': doc.get('notes', ''),
            'status': doc.get('status')
        }
    except Exception as e:
        logger.error(f"CRITICAL ERROR fetching transaction {transaction_id}: {e}", exc_info=True)
        return None

# =========================================================
# GET TRANSACTIONS BY STATUS
# =========================================================
def get_transactions_by_status(username, branch, status):
    db = current_app.db
    if db is None:
        return []
    transactions = []
    try:
        query = {
            'username': username,
            'status': status,
            'parent_id': None,
            '$or': [{'isArchived': {'$exists': False}}, {'isArchived': False}]
        }
        if branch:
            query['branch'] = branch

        for doc in db.transactions.find(query).sort('check_date', -1):
            editor = (
                doc.get('paidBy', doc.get('username', 'N/A')).capitalize()
                if status == 'Paid'
                else doc.get('username', 'N/A').capitalize()
            )
            
            check_date_val = doc.get('check_date')
            check_date_str = 'N/A'
            if isinstance(check_date_val, datetime):
                check_date_str = check_date_val.strftime('%m/%d/%Y')

            due_date_val = doc.get('due_date')
            due_date_str = 'N/A'
            if isinstance(due_date_val, datetime):
                due_date_str = due_date_val.strftime('%m/%d/%Y')

            transaction_info = {
                '_id': str(doc['_id']),
                'name': doc.get('name'),
                'check_date': check_date_str,
                'due_date': due_date_str,
                'editor': editor
            }
            transactions.append(transaction_info)
    except Exception as e:
        logger.error(f"Error fetching transactions: {e}", exc_info=True)
    return transactions

# =========================================================
# GET CHILD TRANSACTIONS
# =========================================================
def get_child_transactions_by_parent_id(username, parent_id):
    """Fetches all child transactions for a given parent ID, regardless of status."""
    db = current_app.db
    if db is None:
        return []
    child_checks = []
    try:
        query = {
            'username': username,
            'parent_id': ObjectId(parent_id),
            '$or': [{'isArchived': {'$exists': False}}, {'isArchived': False}]
        }
        for doc in db.transactions.find(query).sort('createdAt', 1):
            child_checks.append(doc)
    except Exception as e:
        logger.error(f"Error fetching child transactions for parent {parent_id}: {e}", exc_info=True)
    return child_checks

# =========================================================
# UPDATE CHILD TRANSACTION (UPDATED LOGIC)
# =========================================================
def update_child_transaction(username, transaction_id, form_data):
    """Updates an existing child check in the database, calculating amounts from check_amount and deductions."""
    db = current_app.db
    if db is None:
        return False
    try:
        check_amount = float(form_data.get('check_amount') or 0.0)
        deductions = form_data.get('deductions', []) 
        total_deductions = sum(d.get('amount', 0) for d in deductions)
        
        countered_check = check_amount - total_deductions
        
        update_fields = {
            'name': form_data.get('name_of_issued_check'),
            'check_no': form_data.get('check_no'),
            'notes': form_data.get('notes'),
            'check_amount': check_amount,
            'deductions': deductions,
            'countered_check': countered_check,
            'amount': countered_check,
            'ewt': sum(d.get('amount', 0) for d in deductions if d.get('name', '').upper() == 'EWT')
        }
        
        check_date_obj = form_data.get('check_date')
        if check_date_obj:
            update_fields['check_date'] = pytz.utc.localize(datetime.combine(check_date_obj, datetime.min.time()))

        result = db.transactions.update_one(
            {'_id': ObjectId(transaction_id), 'username': username},
            {'$set': update_fields}
        )
        
        if result.modified_count == 1:
            # --- START OF FIX: Recalculate parent folder amount on child update ---
            child_doc = db.transactions.find_one({'_id': ObjectId(transaction_id)})
            if child_doc and child_doc.get('parent_id'):
                _recalculate_parent_folder_amount(db, child_doc['parent_id'], username)
            # --- END OF FIX: Recalculate parent folder amount on child update ---
            return True
            
        return False
    except Exception as e:
        logger.error(f"Error updating child transaction {transaction_id}: {e}", exc_info=True)
        return False

# =========================================================
# MARK FOLDER AS PAID (FIXED)
# =========================================================
def mark_folder_as_paid(username, folder_id, notes):
    db = current_app.db
    if db is None:
        return False
    try:
        paid_at_time = datetime.now(pytz.utc)
        update_data = {
            '$set': {
                'status': 'Paid',
                'paidAt': paid_at_time,
                'paidBy': username
            }
        }
        if notes is not None:
            update_data['$set']['notes'] = notes

        result = db.transactions.update_one(
            {'_id': ObjectId(folder_id), 'username': username},
            update_data
        )

        if result.modified_count == 0:
            logger.warning(f"No document found or updated for folder {folder_id} for user {username}.")
            return False

        db.transactions.update_many(
            {'parent_id': ObjectId(folder_id), 'username': username},
            {'$set': {'status': 'Paid', 'paidAt': paid_at_time}}
        )
        return True
    except Exception as e:
        logger.error(f"Error marking folder {folder_id} as paid: {e}", exc_info=True)
        return False

# =========================================================
# ARCHIVE TRANSACTION
# =========================================================
def archive_transaction(username, transaction_id):
    db = current_app.db
    if db is None:
        return False
    try:
        # --- START OF FIX: Check if it is a child check and grab parent_id before archiving ---
        doc = db.transactions.find_one({'_id': ObjectId(transaction_id)})
        parent_id = doc.get('parent_id') if doc else None
        # --- END OF FIX ---
        
        result = db.transactions.update_one(
            {'_id': ObjectId(transaction_id), 'username': username},
            {'$set': {'isArchived': True, 'archivedAt': datetime.now(pytz.utc)}}
        )
        
        if result.modified_count == 1:
            # --- START OF FIX: Recalculate parent folder amount after child archive ---
            if parent_id:
                _recalculate_parent_folder_amount(db, parent_id, username)
            # --- END OF FIX: Recalculate parent folder amount after child archive ---
            return True
            
        return False
    except Exception as e:
        logger.error(f"Error archiving transaction {transaction_id}: {e}", exc_info=True)
        return False