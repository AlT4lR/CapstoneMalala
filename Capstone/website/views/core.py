from flask import (
    Blueprint, render_template, request, redirect, url_for, session,
    send_from_directory, jsonify
)
from flask_jwt_extended import jwt_required, get_jwt_identity, verify_jwt_in_request
import os
from datetime import datetime, timedelta
import pytz

from . import main # Import the blueprint
from ..models import (
    get_transactions_by_status, get_recent_activity, get_archived_items, 
    log_user_activity, restore_item, delete_item_permanently, 
    save_push_subscription, get_unread_notification_count, 
    get_notifications, mark_single_notification_as_read, # MODIFIED IMPORT
    get_schedules
)

# --- Static Service Worker & Offline Page ---
@main.route('/sw.js')
def service_worker():
    return send_from_directory(os.path.join(main.root_path, '..', 'static', 'js'), 'sw.js', mimetype='application/javascript')

@main.route('/offline')
def offline():
    return render_template('offline.html')

# --- Root & Branch Routes ---
@main.route('/')
def root_route():
    try:
        verify_jwt_in_request(optional=True)
        if get_jwt_identity():
            return redirect(url_for('main.dashboard')) if session.get('selected_branch') else redirect(url_for('main.branches'))
        return redirect(url_for('auth.login'))
    except Exception:
        return redirect(url_for('auth.login'))

@main.route('/branches')
@jwt_required()
def branches():
    return render_template('branches.html')

@main.route('/select_branch/<branch_name>')
@jwt_required()
def select_branch(branch_name):
    if branch_name.upper() in ['MONTALBAN', 'LAGUNA']:
        session['selected_branch'] = branch_name.upper()
    return redirect(url_for('main.dashboard'))

# --- START OF MODIFICATION ---
@main.route('/change_branch')
@jwt_required()
def change_branch():
    """Clears the selected branch from the session to allow re-selection."""
    session.pop('selected_branch', None)
    return redirect(url_for('main.branches'))
# --- END OF MODIFICATION ---

# --- Main Pages ---
@main.route('/dashboard')
@jwt_required()
def dashboard():
    selected_branch = session.get('selected_branch')
    if not selected_branch:
        return redirect(url_for('main.branches'))
    username = get_jwt_identity()
    pending_transactions = get_transactions_by_status(username, selected_branch, 'Pending')
    paid_transactions = get_transactions_by_status(username, selected_branch, 'Paid')
    recent_activities = get_recent_activity(username, limit=10)

    # --- START OF MODIFICATION ---
    start_date = datetime.now(pytz.utc)
    end_date = start_date + timedelta(days=7)
    raw_schedules = get_schedules(username, selected_branch, start_date.isoformat(), end_date.isoformat())

    upcoming_schedules = []
    for schedule in sorted(raw_schedules, key=lambda x: x['start'])[:4]: 
        start_dt = datetime.fromisoformat(schedule['start'])
        end_dt = datetime.fromisoformat(schedule['end']) if schedule.get('end') else start_dt + timedelta(hours=1)
        
        time_range_str = "All-day"
        if not schedule.get('allDay'):
            start_time = start_dt.strftime('%I:%M %p')
            end_time = end_dt.strftime('%I:%M %p')
            time_range_str = f"{start_time} - {end_time}"
            
        upcoming_schedules.append({
            'title': schedule.get('title', 'Untitled Event'),
            'time_range': time_range_str,
            'full_date': start_dt.strftime('%b. %d, %Y'),
        })
    # --- END OF MODIFICATION ---

    return render_template(
        'dashboard.html',
        username=username,
        selected_branch=selected_branch,
        show_sidebar=True,
        pending_count=len(pending_transactions),
        paid_count=len(paid_transactions),
        recent_activities=recent_activities,
        upcoming_schedules=upcoming_schedules
    )

@main.route('/settings')
@jwt_required()
def settings():
    return render_template('settings.html', show_sidebar=True)

@main.route('/archive')
@jwt_required()
def archive():
    username = get_jwt_identity()
    archived_items = get_archived_items(username)
    back_url = request.args.get('back') or url_for('main.dashboard')
    return render_template('_archive.html', show_sidebar=True, archived_items=archived_items, back_url=back_url)

# --- Core API Routes ---
@main.route('/api/activity/recent', methods=['GET'])
@jwt_required()
def get_recent_activity_api():
    username = get_jwt_identity()
    activities = get_recent_activity(username, limit=10)
    return jsonify(activities)

@main.route('/api/save-subscription', methods=['POST'])
@jwt_required()
def save_subscription_route():
    subscription_data = request.get_json()
    if not subscription_data or 'endpoint' not in subscription_data:
        return jsonify({'error': 'Invalid subscription data provided'}), 400
    
    username = get_jwt_identity()
    if save_push_subscription(username, subscription_data):
        return jsonify({'success': True}), 201
    
    return jsonify({'error': 'Failed to save subscription'}), 500

@main.route('/api/notifications/status', methods=['GET'])
@jwt_required()
def notification_status():
    username = get_jwt_identity()
    count = get_unread_notification_count(username)
    return jsonify({'unread_count': count})

@main.route('/api/notifications', methods=['GET'])
@jwt_required()
def get_notifications_route():
    username = get_jwt_identity()
    try:
        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', 25))
    except (ValueError, TypeError):
        return jsonify({'error': 'Invalid page or limit parameter.'}), 400
        
    notifications = get_notifications(username, page, limit)
    return jsonify(notifications)

@main.route('/api/notifications/read/<notification_id>', methods=['POST'])
@jwt_required()
def mark_read_single(notification_id):
    username = get_jwt_identity()
    if mark_single_notification_as_read(username, notification_id):
        return jsonify({'success': True})
    return jsonify({'error': 'Failed to mark notification as read'}), 500
    
@main.route('/api/archive/restore/<item_type>/<item_id>', methods=['POST'])
@jwt_required()
def restore_item_route(item_type, item_id):
    username = get_jwt_identity()
    if restore_item(username, item_type, item_id):
        log_user_activity(username, f'Restored a {item_type.lower()}')
        return jsonify({'success': True}), 200
    return jsonify({'error': f'Failed to restore {item_type.lower()}.'}), 404

@main.route('/api/archive/delete/<item_type>/<item_id>', methods=['DELETE'])
@jwt_required()
def delete_item_permanently_route(item_type, item_id):
    username = get_jwt_identity()
    if delete_item_permanently(username, item_type, item_id):
        log_user_activity(username, f'Permanently deleted a {item_type.lower()}')
        return jsonify({'success': True}), 200
    return jsonify({'error': 'An unexpected error occurred.'}), 500