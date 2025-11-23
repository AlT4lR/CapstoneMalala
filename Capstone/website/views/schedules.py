# website/views/schedules.py

from flask import render_template, request, jsonify, url_for, session
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime
import logging

from . import main # Import the blueprint
from ..models import (
    log_user_activity, add_schedule, get_schedules, 
    update_schedule, delete_schedule, add_notification
)

@main.route('/schedules')
@jwt_required()
def schedules():
    return render_template('schedules.html', show_sidebar=True)

# --- Schedule API Routes ---
@main.route('/api/schedules', methods=['GET'])
@jwt_required()
def get_schedules_route():
    username = get_jwt_identity()
    selected_branch = session.get('selected_branch')
    if not selected_branch:
        return jsonify({"error": "Branch not selected"}), 400
    
    start, end = request.args.get('start'), request.args.get('end')
    if not start or not end: 
        return jsonify({"error": "Start and end date are required"}), 400
    
    return jsonify(get_schedules(username, selected_branch, start, end))
# Configure logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.ERROR)

@main.route('/api/schedules/add', methods=['POST'])
@jwt_required()
def add_schedule_route():
    username = get_jwt_identity()
    selected_branch = session.get('selected_branch')
    if not selected_branch:
        return jsonify({"error": "Branch not selected"}), 400
        
    data = request.get_json()
    if not data: 
        return jsonify({"error": "JSON data is missing"}), 400
        
    if add_schedule(username, selected_branch, data):
        log_user_activity(username, "Created a new schedule")
        
        # Robust Notification Logic
        schedule_title = data.get('title', 'a new event')
        schedule_date_str = data.get('date', '')
        
        try:
            date_obj = datetime.strptime(schedule_date_str, '%Y-%m-%d')
            formatted_date = date_obj.strftime('%B %d, %Y')
            
            message = f"Your event '{schedule_title}' is scheduled for {formatted_date}."
            notification_url = url_for('main.schedules', _external=False)
            
            add_notification(username, "New Event Created", message, notification_url)
            
        except ValueError:
            logger.warning(f"Failed to parse date for new schedule notification: {schedule_date_str}. Notification skipped.")
        except Exception as e:
            logger.error(f"Failed to create notification for new schedule: {e}")

        return jsonify({"success": True})
        
    return jsonify({"error": "Failed to create schedule"}), 500

@main.route('/api/schedules/update/<schedule_id>', methods=['POST'])
@jwt_required()
def update_schedule_route(schedule_id):
    username = get_jwt_identity()
    data = request.get_json()
    if not data: 
        return jsonify({'error': 'Invalid data'}), 400
        
    if update_schedule(username, schedule_id, data):
        log_user_activity(username, "Updated a schedule")
        
        schedule_title = data.get('title', 'an event')
        message = f"Your event '{schedule_title}' has been updated."
        notification_url = url_for('main.schedules', _external=False)
        add_notification(username, "Event Updated", message, notification_url)

        return jsonify({'success': True})
        
    return jsonify({'error': 'Update failed'}), 500

@main.route('/api/schedules/<schedule_id>', methods=['DELETE'])
@jwt_required()
def delete_schedule_route(schedule_id):
    username = get_jwt_identity()
    if delete_schedule(username, schedule_id):
        log_user_activity(username, "Deleted a schedule")
        return jsonify({'success': True})
    
    return jsonify({'error': 'Schedule not found or delete failed.'}), 404