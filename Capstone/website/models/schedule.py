# website/models/schedule.py

import logging
from datetime import datetime
import pytz
from bson.objectid import ObjectId
from flask import current_app

logger = logging.getLogger(__name__)

def add_schedule(username, branch, data):
    """Adds a new schedule to the database."""
    db = current_app.db
    if db is None: return False
    try:
        start_dt = datetime.fromisoformat(data['start'].replace('Z', '+00:00'))
        end_dt = datetime.fromisoformat(data['end'].replace('Z', '+00:00')) if data.get('end') else None

        schedule_doc = {
            'username': username,
            'branch': branch,
            'title': data.get('title', 'Untitled Event'),
            'description': data.get('description', ''),
            'location': data.get('location', ''),
            'label': data.get('label', 'Others'),
            'allDay': data.get('allDay', False),
            'start': start_dt,
            'end': end_dt,
            'createdAt': datetime.now(pytz.utc)
        }
        db.schedules.insert_one(schedule_doc)
        return True
    except Exception as e:
        logger.error(f"Error adding schedule for {username}: {e}", exc_info=True)
        return False

def get_schedules(username, branch, start_str, end_str):
    """Fetches schedules for a given user, branch, and date range."""
    db = current_app.db
    if db is None: return []
    
    try:
        start_dt = datetime.fromisoformat(start_str.replace('Z', '+00:00'))
        end_dt = datetime.fromisoformat(end_str.replace('Z', '+00:00'))

        query = {
            'username': username,
            'branch': branch,
            'start': {'$gte': start_dt, '$lt': end_dt}
        }
        
        schedules_list = []
        for doc in db.schedules.find(query):
            schedules_list.append({
                'id': str(doc['_id']),
                'title': doc.get('title'),
                'start': doc['start'].isoformat(),
                'end': doc['end'].isoformat() if doc.get('end') else None,
                'allDay': doc.get('allDay', False),
                'description': doc.get('description', ''),
                'location': doc.get('location', ''),
                'label': doc.get('label', 'Others')
            })
        return schedules_list
    except Exception as e:
        logger.error(f"Error fetching schedules for {username}: {e}", exc_info=True)
        return []

def update_schedule(username, schedule_id, data):
    """Updates an existing schedule in the database."""
    db = current_app.db
    if db is None: return False
    try:
        start_dt = datetime.fromisoformat(data['start'].replace('Z', '+00:00'))
        end_dt = datetime.fromisoformat(data['end'].replace('Z', '+00:00')) if data.get('end') else None
        
        update_doc = {
            '$set': {
                'title': data.get('title'),
                'description': data.get('description'),
                'location': data.get('location'),
                'label': data.get('label'),
                'allDay': data.get('allDay'),
                'start': start_dt,
                'end': end_dt,
            }
        }
        result = db.schedules.update_one({'_id': ObjectId(schedule_id), 'username': username}, update_doc)
        return result.modified_count > 0
    except Exception as e:
        logger.error(f"Error updating schedule {schedule_id}: {e}", exc_info=True)
        return False

def delete_schedule(username, schedule_id):
    """Deletes a schedule from the database."""
    db = current_app.db
    if db is None: return False
    try:
        result = db.schedules.delete_one({'_id': ObjectId(schedule_id), 'username': username})
        return result.deleted_count > 0
    except Exception as e:
        logger.error(f"Error deleting schedule {schedule_id}: {e}", exc_info=True)
        return False