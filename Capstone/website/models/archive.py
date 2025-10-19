# website/models/archive.py

import logging
from datetime import datetime
import pytz
from bson.objectid import ObjectId
from flask import current_app
from .helpers import format_relative_time

logger = logging.getLogger(__name__)

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
                    'relative_time': format_relative_time(doc.get('archivedAt')) if doc.get('archivedAt') else 'N/A'
                })
        except Exception as e:
            logger.error(f"Error fetching archived items from {collection_name} for {username}: {e}")
    items.sort(key=lambda x: x['relative_time'], reverse=True)
    return items