# website/models/schedule.py

import logging
from datetime import datetime, timedelta
import pytz
from bson.objectid import ObjectId
from flask import current_app

logger = logging.getLogger(__name__)

# ✅ START OF FIX: This function is now fully JSON-compatible
def add_schedule(username, branch, schedule_data):
    db = current_app.db
    if db is None: return False
    try:
        is_all_day = schedule_data.get('allDay', False)
        date_str = schedule_data.get('date')

        # When creating from a JSON payload, the JS sends pre-formatted ISO strings
        start_dt = datetime.fromisoformat(schedule_data['start'].replace('Z', '+00:00'))
        
        if is_all_day:
            # For all-day events, the end date is not sent from the JS payload, so we calculate it
            end_dt = start_dt + timedelta(days=1)
        else:
            end_dt = datetime.fromisoformat(schedule_data['end'].replace('Z', '+00:00'))
        
        db.schedules.insert_one({
            'username': username,
            'branch': branch,
            'title': schedule_data.get('title'),
            'description': schedule_data.get('description'),
            'location': schedule_data.get('location'),
            'label': schedule_data.get('label', 'Others'),
            'start': start_dt.replace(tzinfo=pytz.utc),
            'end': end_dt.replace(tzinfo=pytz.utc),
            'allDay': is_all_day,
            'createdAt': datetime.now(pytz.utc)
        })
        return True
    except (KeyError, TypeError, ValueError) as e:
        # Catch potential errors if the JSON payload is malformed
        logger.error(f"Error parsing schedule JSON for {username}: {e}", exc_info=True)
        return False
# ✅ END OF FIX

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
                'location': doc.get('location'),
                'label': doc.get('label', 'Others')
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
        if 'label' in data:
            update_fields['label'] = data['label']
        
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