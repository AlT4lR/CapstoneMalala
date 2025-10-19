# website/models/loan.py

import logging
from datetime import datetime
import pytz
from flask import current_app

logger = logging.getLogger(__name__)

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