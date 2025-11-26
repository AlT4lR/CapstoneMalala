# website/models/transaction.py

import logging
from datetime import datetime
import pytz
from bson import ObjectId
from bson.objectid import ObjectId
from flask import current_app

logger = logging.getLogger(__name__)


# =========================================================
# HELPER: Recompute and store folder totals
# =========================================================
def recompute_folder_totals(username, parent_id):
    """
    Recomputes totals for a folder (parent transaction) and stores them.
    Fields stored:
      - amount              (Total Check Amount To Pay, now holding SUM(child.check_amount))
      - countered_check     (Total Countered Check, now holding SUM(child.countered_check))
      - ewt                 (Total EWT, now holding SUM(child.ewt))
    """
    db = current_app.db
    if db is None:
        logger.error("No DB available in recompute_folder_totals()")
        return False

    try:
        if parent_id is None:
            logger.debug("recompute_folder_totals called with parent_id=None")
            return False

        pid = ObjectId(parent_id) if not isinstance(parent_id, ObjectId) else parent_id

        # Query to match all non-archived children for the parent folder
        query = {
            'username': username,
            'parent_id': pid,
            '$or': [{'isArchived': {'$exists': False}}, {'isArchived': False}]
        }

        # Aggregate the required sums in a single step
        pipeline = [
            {'$match': query},
            {'$group': {
                '_id': '$parent_id',
                'total_check_amount': {'$sum': '$check_amount'},     # The new Target Debt
                'total_countered_check': {'$sum': '$countered_check'}, # The new Covered Debt
                'total_ewt': {'$sum': '$ewt'}
            }}
        ]

        result = list(db.transactions.aggregate(pipeline))

        # Get results, defaulting to 0.0 if no children exist
        totals = result[0] if result else {}
        check_amount_sum = totals.get('total_check_amount', 0.0)
        countered_check_sum = totals.get('total_countered_check', 0.0)
        ewt_sum = totals.get('total_ewt', 0.0)
        
        # Update the parent folder with the correct, separate running totals
        update_fields = {
            'amount': round(check_amount_sum, 2),        # Parent.amount = SUM(Child.check_amount) -> Total Debt
            'countered_check': round(countered_check_sum, 2), # Parent.countered_check = SUM(Child.countered_check) -> Covered Debt
            'ewt': round(ewt_sum, 2)                      # Parent.ewt = SUM(Child.ewt)
        }

        result = db.transactions.update_one(
            {'_id': pid, 'username': username},
            {'$set': update_fields}
        )

        if result.modified_count:
            logger.info(f"Recomputed totals for folder {parent_id}: {update_fields}")
        else:
            logger.debug(f"Recompute totals: no modification for folder {parent_id}.")
        return True
    except Exception as e:
        logger.error(f"Error recomputing folder totals for parent {parent_id}: {e}", exc_info=True)
        return False


# =========================================================
# UPDATE TRANSACTION (for Folders)
# =========================================================
def update_transaction(username, transaction_id, form_data):
    """Updates an existing transaction FOLDER in the database."""
    db = current_app.db
    if db is None:
        return False
    try:
        update_fields = {
            'name': form_data.get('name'),
            'notes': form_data.get('notes') 
        }
        
        if 'amount' in form_data:
            try:
                update_fields['amount'] = float(form_data['amount'])
            except (ValueError, TypeError):
                pass 

        check_date_str = form_data.get('check_date')
        if check_date_str:
            try:
                date_part = datetime.strptime(check_date_str, '%Y-%m-%d').date()
                update_fields['check_date'] = pytz.utc.localize(datetime.combine(date_part, datetime.min.time()))
            except ValueError: pass
        
        due_date_str = form_data.get('due_date')
        if due_date_str:
            try:
                date_part = datetime.strptime(due_date_str, '%Y-%m-%d').date()
                update_fields['due_date'] = pytz.utc.localize(datetime.combine(date_part, datetime.min.time()))
            except ValueError: pass
        else:
            update_fields['$unset'] = {'due_date': ""}

        set_updates = {k: v for k, v in update_fields.items() if k not in ['$unset', 'notes']}
        set_updates['notes'] = update_fields.get('notes', '')
        
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
            doc['amount'] = float(transaction_data.get('amount') or 0.0)
            doc['countered_check'] = 0.0 
            doc['ewt'] = 0.0             
            doc['check_amount'] = 0.0
            doc['deductions'] = []
            doc['total_to_pay'] = 0.0    
        else: # This is a CHILD CHECK
            check_amount = float(transaction_data.get('check_amount') or 0.0)
            deductions = transaction_data.get('deductions', [])
            
            doc['check_amount'] = round(check_amount, 2)
            doc['deductions'] = deductions
            
            # --- START OF MODIFICATION: No Auto-Balancing ---
            # Only use manual input. If empty or invalid, default to 0.0
            manual_countered = transaction_data.get('countered_check')
            if manual_countered is not None and str(manual_countered).strip() != '':
                try:
                    countered_check = round(float(manual_countered), 2)
                except ValueError:
                    countered_check = 0.0
            else:
                countered_check = 0.0
            # --- END OF MODIFICATION ---

            doc['countered_check'] = countered_check
            doc['amount'] = countered_check 
            
            doc['ewt'] = round(sum(d.get('amount', 0) for d in deductions if d.get('name', '').upper() == 'EWT'), 2)

        db.transactions.insert_one(doc)
        
        if parent_id:
            recompute_folder_totals(username, parent_id)
        
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
        logger.error(f"Error fetching transaction {transaction_id}: {e}", exc_info=True)
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
    """Updates an existing child check in the database."""
    db = current_app.db
    if db is None:
        return False
    try:
        # Fetch existing doc to find parent_id (for recompute afterwards)
        existing = db.transactions.find_one({'_id': ObjectId(transaction_id), 'username': username})
        parent_id = existing.get('parent_id') if existing else None

        check_amount = float(form_data.get('check_amount') or 0.0)
        deductions = form_data.get('deductions', []) 
        
        # --- START OF MODIFICATION: No Auto-Balancing ---
        manual_countered = form_data.get('countered_check')
        if manual_countered is not None and str(manual_countered).strip() != '':
            try:
                countered_check = round(float(manual_countered), 2)
            except ValueError:
                countered_check = 0.0
        else:
            countered_check = 0.0
        # --- END OF MODIFICATION ---
        
        ewt = round(sum(d.get('amount', 0) for d in deductions if d.get('name', '').upper() == 'EWT'), 2)
        
        update_fields = {
            'name': form_data.get('name_of_issued_check'),
            'check_no': form_data.get('check_no'),
            'notes': form_data.get('notes'),
            'check_amount': round(check_amount, 2),
            'deductions': deductions, 
            'countered_check': countered_check, 
            'amount': countered_check,         
            'ewt': ewt                         
        }
        
        check_date_str = form_data.get('check_date')
        if check_date_str:
            try:
                date_part = datetime.strptime(check_date_str, '%Y-%m-%d').date()
                update_fields['check_date'] = pytz.utc.localize(datetime.combine(date_part, datetime.min.time()))
            except ValueError:
                logger.warning(f"Failed to parse check_date string '{check_date_str}' in update_child_transaction.")

        result = db.transactions.update_one(
            {'_id': ObjectId(transaction_id), 'username': username},
            {'$set': update_fields}
        )
        
        if result.modified_count == 1 and parent_id:
            recompute_folder_totals(username, parent_id)
            return True
            
        return result.matched_count == 1 
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
    """
    Archives a transaction. If the archived transaction is a child,
    recompute its parent's totals after archiving.
    """
    db = current_app.db
    if db is None:
        return False
    try:
        doc = db.transactions.find_one({'_id': ObjectId(transaction_id), 'username': username})
        if not doc:
            logger.warning(f"archive_transaction: transaction {transaction_id} not found for user {username}")
            return False

        parent_id = doc.get('parent_id')

        result = db.transactions.update_one(
            {'_id': ObjectId(transaction_id), 'username': username},
            {'$set': {'isArchived': True, 'archivedAt': datetime.now(pytz.utc)}}
        )

        success = result.modified_count == 1

        if success and parent_id:
            try:
                recompute_folder_totals(username, parent_id)
            except Exception:
                logger.exception("Failed to recompute folder totals after archiving child.")

        return success
    except Exception as e:
        logger.error(f"Error archiving transaction {transaction_id}: {e}", exc_info=True)
        return False