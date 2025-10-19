# website/models/invoice.py

import logging
from datetime import datetime
import pytz
from bson.objectid import ObjectId
from flask import current_app

logger = logging.getLogger(__name__)

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