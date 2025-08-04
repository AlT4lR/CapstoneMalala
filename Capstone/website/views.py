# website/views.py

from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify, make_response, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime, timedelta
import pytz # Required for timezone handling in schedule functions
from .models import (
    add_category, get_user_by_username, # Assuming these are accessible via app proxy
    add_schedule, get_schedules_by_date_range, get_all_categories
)
import logging

logger = logging.getLogger(__name__)

main = Blueprint('main', __name__)

# --- Static Data Definitions (Mock Data - Replace with DB queries) ---
# Note: These should ideally come from config or a database.
# BRANCH_CATEGORIES and their icons are used for branch selection.
BRANCH_CATEGORIES = [
    {'name': 'DOUBLE L', 'icon': 'building_icon.png'},
    {'name': 'SUB-URBAN', 'icon': 'building_icon.png'},
    {'name': 'KASIGLAHAN', 'icon': 'building_icon.png'},
    {'name': 'SOUTHVILLE 8B', 'icon': 'building_icon.png'},
    {'name': 'SITIO TANAG', 'icon': 'building_icon.png'}
]

# Mock transaction data. In a real app, this would be fetched from DB.
# Added 'branch' key to each transaction for filtering.
transactions_data = [
    {'id': '#123456', 'name': 'Jody Sta. Maria', 'date': '2025-05-30', 'time': '10:30 AM', 'amount': 999.00, 'method': 'Bank-to-Bank', 'status': 'Pending', 'notes': 'Initial deposit.', 'branch': 'DOUBLE L'},
    {'id': '#246810', 'name': 'Nenia Ann Valenzuela', 'date': '2025-05-30', 'time': '11:49 AM', 'amount': 10000.00, 'method': 'Bank-to-Bank', 'status': 'Paid', 'notes': 'Payment for design services.', 'branch': 'DOUBLE L'},
    {'id': '#368912', 'name': 'Jessilyn Telma', 'date': '2025-06-12', 'time': '02:15 PM', 'amount': 20000.00, 'method': 'Bank-to-Bank', 'status': 'Paid', 'notes': 'Invoice #INV-2025-06-01', 'branch': 'SUB-URBAN'},
    {'id': '#481216', 'name': 'Shuvee Entrata', 'date': '2025-06-17', 'time': '09:00 AM', 'amount': 2000.00, 'method': 'Bank-to-Bank', 'status': 'Pending', 'notes': 'Service fee.', 'branch': 'SUB-URBAN'},
    {'id': '#5101520', 'name': 'Will Ashley', 'date': '2025-07-01', 'time': '03:45 PM', 'amount': 80000.00, 'method': 'Bank-to-Bank', 'status': 'Pending', 'notes': 'Project completion payment.', 'branch': 'KASIGLAHAN'},
    {'id': '#6121824', 'name': 'Brent Manalo', 'date': '2025-07-01', 'time': '04:00 PM', 'amount': 80000.00, 'method': 'Bank-to-Bank', 'status': 'Pending', 'notes': 'New Project Payment.', 'branch': 'SOUTHVILLE 8B'},
    {'id': '#6121825', 'name': 'Charlie Fleming', 'date': '2025-07-01', 'time': '04:30 PM', 'amount': 80000.00, 'method': 'Bank-to-Bank', 'status': 'Pending', 'notes': 'Consultation Fee.', 'branch': 'SITIO TANAG'},
    {'id': '#7000000', 'name': 'Alice Smith', 'date': '2025-07-02', 'time': '10:00 AM', 'amount': 5000.00, 'method': 'Cash', 'status': 'Paid', 'notes': 'Consultation.', 'branch': 'DOUBLE L'},
]

# Mock notifications data
dummy_inbox_notifications = [
    {'id': 1, 'name': 'Security Bank', 'preview': 'Bill for the week Dear valued customerh', 'date': '30 May 2025, 2:00 PM', 'icon': 'security_bank_icon.png'},
    {'id': 2, 'name': 'New Message', 'preview': 'You have a new message from support.', 'date': 'July 1, 2025, 1:00 PM', 'icon': 'message_icon.png'},
    {'id': 3, 'name': 'Reminder', 'preview': 'Review pending payments.', 'date': 'July 2, 2025, 9:00 AM', 'icon': 'reminder_icon.png'},
]

# Mock data for analytics charts (branch-specific budgets)
ALL_BRANCH_BUDGET_DATA = {
    'DOUBLE L': [
        { 'label': 'Income', 'value': 40, 'color': '#facc15' },
        { 'label': 'Spent', 'value': 20, 'color': '#a855f7' },
        { 'label': 'Savings', 'value': 30, 'color': '#ec4899' },
        { 'label': 'Scheduled', 'value': 10, 'color': '#3b82f6' }
    ],
    'SUB-URBAN': [
        { 'label': 'Income', 'value': 30, 'color': '#facc15' },
        { 'label': 'Spent', 'value': 25, 'color': '#a855f7' },
        { 'label': 'Savings', 'value': 35, 'color': '#ec4899' },
        { 'label': 'Scheduled', 'value': 10, 'color': '#3b82f6' }
    ],
    'KASIGLAHAN': [
        { 'label': 'Income', 'value': 50, 'color': '#facc15' },
        { 'label': 'Spent', 'value': 15, 'color': '#a855f7' },
        { 'label': 'Savings', 'value': 20, 'color': '#ec4899' },
        { 'label': 'Scheduled', 'value': 15, 'color': '#3b82f6' }
    ],
    'SOUTHVILLE 8B': [
        { 'label': 'Income', 'value': 25, 'color': '#facc15' },
        { 'label': 'Spent', 'value': 40, 'color': '#a855f7' },
        { 'label': 'Savings', 'value': 20, 'color': '#ec4899' },
        { 'label': 'Scheduled', 'value': 15, 'color': '#3b82f6' }
    ],
    'SITIO TANAG': [
        { 'label': 'Income', 'value': 35, 'color': '#facc15' },
        { 'label': 'Spent', 'value': 30, 'color': '#a855f7' },
        { 'label': 'Savings', 'value': 20, 'color': '#ec4899' },
        { 'label': 'Scheduled', 'value': 15, 'color': '#3b82f6' }
    ],
    'DEFAULT': [ # Data for when no specific branch is selected
        { 'label': 'Income', 'value': 10, 'color': '#facc15' },
        { 'label': 'Spent', 'value': 20, 'color': '#a855f7' },
        { 'label': 'Savings', 'value': 30, 'color': '#ec4899' },
        { 'label': 'Scheduled', 'value': 40, 'color': '#3b82f6' }
    ]
}

# Mock data for archived items
archived_items_data = [
    {'name': 'Nenia Ann Valenzuela', 'id': '#246810', 'datetime': '2025-07-01T10:30:00', 'relative_time': '45 minutes ago'},
    {'name': 'Jessilyn Telma', 'id': '#368912', 'datetime': '2025-07-01T10:30:00', 'relative_time': '45 minutes ago'}
]

# Mock data for analytics revenue chart
analytics_revenue_data = {
    'month': 'MAY 2025',
    'labels': ['Week 1', 'Week 2', 'Week 3', 'Week 4', 'Week 5'],
    'legend': [
        {'label': 'P 100,000', 'color': '#ff0000'}, # Example colors
        {'label': 'P 200,000', 'color': '#ffff00'},
        {'label': 'P 250,000', 'color': '#00ff00'},
        {'label': 'P 500,000', 'color': '#00ffff'},
        {'label': 'P 700,000', 'color': '#0000ff'},
        {'label': 'P 1,000,000', 'color': '#ff00ff'},
    ],
    'data': [
        {'value': 'P 200,000', 'percentage': 25, 'color': '#ffff00'},
        {'value': 'P 500,000', 'percentage': 50, 'color': '#00ffff'},
        {'value': 'P 700,000', 'percentage': 70, 'color': '#0000ff'},
        {'value': 'P 1,100,000 (Proj.)', 'percentage': 100, 'color': '#d1d5db'}
    ]
}

# Mock data for analytics supplier performance
analytics_supplier_data = [
    {'name': 'Vincent Lee', 'score': 89, 'delivery': 96, 'defects': 1.2, 'variance': 2.1, 'lead_time': 5.2},
    {'name': 'Anthony Lee', 'score': 72, 'delivery': 82, 'defects': 3.5, 'variance': -1.8, 'lead_time': 7.3},
    {'name': 'Vincent Lee', 'score': 89, 'delivery': 96, 'defects': 1.2, 'variance': 2.1, 'lead_time': 5.2}, # Duplicate for demo
    {'name': 'Anthony Lee', 'score': 72, 'delivery': 82, 'defects': 3.5, 'variance': -1.8, 'lead_time': 7.3}, # Duplicate for demo
]

# --- Route Definitions ---

@main.route('/branches')
@jwt_required()
def branches():
    current_user_identity = get_jwt_identity()
    return render_template('branches.html',
                           username=current_user_identity,
                           branches=BRANCH_CATEGORIES,
                           inbox_notifications=dummy_inbox_notifications,
                           show_notifications_button=True)

@main.route('/select_branch/<branch_name>')
@jwt_required()
def select_branch(branch_name):
    """Sets the selected branch in the session and redirects to dashboard."""
    session['selected_branch'] = branch_name
    logger.info(f"User '{get_jwt_identity()}' selected branch: {branch_name}")
    return redirect(url_for('main.dashboard'))

@main.route('/')
@main.route('/dashboard')
@jwt_required()
def dashboard():
    current_user_identity = get_jwt_identity()
    selected_branch = session.get('selected_branch')
    
    if not selected_branch:
        flash("Please select a branch first.", "info")
        return redirect(url_for('main.branches'))

    # Retrieve budget data specific to the selected branch, fallback to 'DEFAULT'
    current_budget_data = ALL_BRANCH_BUDGET_DATA.get(selected_branch, ALL_BRANCH_BUDGET_DATA['DEFAULT'])

    return render_template('dashboard.html',
                           username=current_user_identity, 
                           selected_branch=selected_branch,
                           inbox_notifications=dummy_inbox_notifications,
                           chart_data=current_budget_data, # Pass branch-specific data
                           show_notifications_button=True)

# Redundant route, kept for completeness but could be removed.
# @main.route('/transactions')
# @jwt_required()
# def transactions():
#     return redirect(url_for('main.transactions_paid'))

@main.route('/transactions/paid')
@jwt_required()
def transactions_paid():
    current_user_identity = get_jwt_identity()
    selected_branch = session.get('selected_branch')

    if not selected_branch:
        flash("Please select a branch to view transactions.", "info")
        return redirect(url_for('main.branches'))
    
    # Filter transactions based on selected branch and status 'Paid'
    paid_transactions = [t for t in transactions_data if t['status'] == 'Paid' and t['branch'] == selected_branch]
    
    return render_template('paid_transactions.html',
                           username=current_user_identity,
                           selected_branch=selected_branch,
                           transactions=paid_transactions,
                           inbox_notifications=dummy_inbox_notifications,
                           current_filter='paid',
                           show_notifications_button=True)

@main.route('/transactions/pending')
@jwt_required()
def transactions_pending():
    current_user_identity = get_jwt_identity()
    selected_branch = session.get('selected_branch')

    if not selected_branch:
        flash("Please select a branch to view transactions.", "info")
        return redirect(url_for('main.branches'))
    
    # Filter transactions based on selected branch and status 'Pending'
    pending_transactions = [t for t in transactions_data if t['status'] == 'Pending' and t['branch'] == selected_branch]
    
    return render_template('pending_transactions.html',
                           username=current_user_identity,
                           selected_branch=selected_branch,
                           transactions=pending_transactions,
                           inbox_notifications=dummy_inbox_notifications,
                           current_filter='pending',
                           show_notifications_button=True)

@main.route('/add-transaction', methods=['GET', 'POST'])
@jwt_required()
def add_transaction():
    current_user_identity = get_jwt_identity()
    selected_branch = session.get('selected_branch') 

    if not selected_branch:
        flash("Please select a branch before adding a transaction.", "error")
        return redirect(url_for('main.branches'))

    if request.method == 'POST':
        name = request.form.get('name')
        transaction_id = request.form.get('transaction_id')
        date_time_str = request.form.get('date_time') # e.g., "2023-10-27T10:30"
        amount = request.form.get('amount')
        payment_method = request.form.get('payment_method')
        status = request.form.get('status')

        # Basic validation
        if not all([name, transaction_id, date_time_str, amount, payment_method, status]):
            flash('All transaction fields are required.', 'error')
            return render_template('add_transaction.html', # Re-render form with data
                                   username=current_user_identity,
                                   selected_branch=selected_branch,
                                   inbox_notifications=dummy_inbox_notifications,
                                   show_notifications_button=True,
                                   # Pass form data back
                                   transaction_data={
                                       'name': name, 'transaction_id': transaction_id, 
                                       'date_time': date_time_str, 'amount': amount, 
                                       'payment_method': payment_method, 'status': status
                                   })

        try:
            # Convert date_time string to datetime object for consistent storage/use
            # Assume local time if no timezone info, or parse as UTC if format implies it (e.g., with 'Z')
            # For simplicity here, parsing directly; in real app, handle timezones carefully.
            transaction_datetime = datetime.strptime(date_time_str, '%Y-%m-%dT%H:%M')
            transaction_date_display = transaction_datetime.strftime('%m/%d/%Y')
            transaction_time_display = transaction_datetime.strftime('%I:%M %p')

            # Add to mock data (replace with DB call)
            transactions_data.append({
                'id': transaction_id,
                'name': name,
                'date': transaction_date_display,
                'time': transaction_time_display,
                'amount': float(amount),
                'method': payment_method,
                'status': status,
                'notes': 'Added via form.',
                'branch': selected_branch
            })

            flash('Successfully Added a Transaction!', 'success')
            
            # Redirect based on status
            if status == 'Paid':
                return redirect(url_for('main.transactions_paid'))
            elif status == 'Pending':
                return redirect(url_for('main.transactions_pending'))
            else: # Default redirect if status is unexpected
                return redirect(url_for('main.transactions_paid'))

        except ValueError:
            flash('Invalid date or amount format.', 'error')
            return render_template('add_transaction.html', # Re-render form with data
                                   username=current_user_identity,
                                   selected_branch=selected_branch,
                                   inbox_notifications=dummy_inbox_notifications,
                                   show_notifications_button=True,
                                   transaction_data={
                                       'name': name, 'transaction_id': transaction_id, 
                                       'date_time': date_time_str, 'amount': amount, 
                                       'payment_method': payment_method, 'status': status
                                   })

    # For GET request, render the form
    return render_template('add_transaction.html',
                           username=current_user_identity,
                           selected_branch=selected_branch,
                           inbox_notifications=dummy_inbox_notifications,
                           show_notifications_button=True)

@main.route('/archive')
@jwt_required()
def archive():
    current_user_identity = get_jwt_identity()
    return render_template('_archive.html', # Note: Template name was _archive.html, changed to archive.html for consistency if intended
                           username=current_user_identity,
                           selected_branch=session.get('selected_branch'),
                           archived_items=archived_items_data,
                           inbox_notifications=dummy_inbox_notifications,
                           show_notifications_button=True)

@main.route('/billings')
@jwt_required()
def wallet(): # Route name 'wallet' for 'billings.html' template
    current_user_identity = get_jwt_identity()
    return render_template('billings.html',
                           username=current_user_identity,
                           selected_branch=session.get('selected_branch'),
                           inbox_notifications=dummy_inbox_notifications,
                           show_notifications_button=True)

@main.route('/analytics')
@jwt_required()
def analytics():
    current_user_identity = get_jwt_identity()
    selected_branch = session.get('selected_branch')
    
    if not selected_branch:
        flash("Please select a branch to view analytics.", "info")
        return redirect(url_for('main.branches'))

    # Use branch-specific data or default
    current_revenue_data = ALL_BRANCH_BUDGET_DATA.get(selected_branch, ALL_BRANCH_BUDGET_DATA['DEFAULT'])
    
    return render_template('analytics.html',
                           username=current_user_identity,
                           selected_branch=selected_branch,
                           revenue_data=analytics_revenue_data, # This seems to be static, not branch-specific based on mock data
                           suppliers=analytics_supplier_data,
                           inbox_notifications=dummy_inbox_notifications,
                           show_notifications_button=True)

@main.route('/notifications')
@jwt_required()
def notifications():
    current_user_identity = get_jwt_identity()
    return render_template('notifications.html',
                           username=current_user_identity,
                           selected_branch=session.get('selected_branch'),
                           inbox_notifications=dummy_inbox_notifications,
                           show_notifications_button=True)

@main.route('/invoice')
@jwt_required()
def invoice():
    current_user_identity = get_jwt_identity()
    return render_template('invoice.html',
                           username=current_user_identity,
                           selected_branch=session.get('selected_branch'),
                           inbox_notifications=dummy_inbox_notifications,
                           show_notifications_button=True)

@main.route('/schedules', methods=['GET'])
@jwt_required()
def schedules():
    current_user_identity = get_jwt_identity()
    selected_branch = session.get('selected_branch')

    if not selected_branch:
        flash("Please select a branch to view schedules.", "info")
        return redirect(url_for('main.branches'))

    # Fetch categories for the user from models
    categories = current_app.get_all_categories(current_user_identity)

    # Determine current date for calendar view
    today = datetime.now(pytz.utc) # Use timezone-aware datetime (UTC)
    year = request.args.get('year', type=int)
    month = request.args.get('month', type=int)
    day = request.args.get('day', type=int)

    if year and month and day:
        try:
            current_date = datetime(year, month, day, tzinfo=pytz.utc)
        except ValueError:
            flash("Invalid date parameters.", "error")
            current_date = today # Fallback to today
    elif year and month:
        try:
            current_date = datetime(year, month, 1, tzinfo=pytz.utc) # Default to 1st of month
        except ValueError:
            flash("Invalid year or month.", "error")
            current_date = today
    else:
        current_date = today

    # Calculate start date for mini-calendar (ensure it starts on a Sunday)
    first_day_of_month = current_date.replace(day=1)
    # Go back to the previous Sunday
    mini_cal_start_date = first_day_of_month - timedelta(days=first_day_of_month.weekday() + 1)
    # Ensure it's truly Sunday (weekday() returns 0 for Monday, 6 for Sunday)
    if mini_cal_start_date.weekday() != 6:
        mini_cal_start_date -= timedelta(days=(mini_cal_start_date.weekday() + 1) % 7)
    mini_cal_start_date = mini_cal_start_date.replace(tzinfo=pytz.utc) # Make it UTC aware

    return render_template('schedules.html',
                           username=current_user_identity,
                           selected_branch=selected_branch,
                           inbox_notifications=dummy_inbox_notifications,
                           show_notifications_button=True,
                           current_date=current_date,
                           categories=categories,
                           mini_cal_start_date=mini_cal_start_date)

@main.route('/api/schedules', methods=['GET'])
@jwt_required()
def api_get_schedules():
    current_user_identity = get_jwt_identity()
    start_date_str = request.args.get('start')
    end_date_str = request.args.get('end')

    if not start_date_str or not end_date_str:
        return jsonify({'error': 'Missing start or end date parameters.'}), 400

    try:
        # Parse ISO 8601 dates, ensuring they are UTC timezone-aware
        start_date = datetime.fromisoformat(start_date_str.replace('Z', '+00:00')).astimezone(pytz.utc)
        end_date = datetime.fromisoformat(end_date_str.replace('Z', '+00:00')).astimezone(pytz.utc)
    except ValueError:
        return jsonify({'error': 'Invalid date format. Use ISO 8601 (YYYY-MM-DDTHH:MM:SS.sssZ or similar).'}), 400

    schedules = current_app.get_schedules_by_date_range(current_user_identity, start_date, end_date) # Access model func via app proxy
    
    # API response should have ISO format datetimes (UTC)
    return jsonify(schedules)

@main.route('/api/schedules', methods=['POST'])
@jwt_required()
def api_create_schedule():
    current_user_identity = get_jwt_identity()
    data = request.get_json()

    if not data:
        return jsonify({'error': 'No JSON data provided.'}), 400

    title = data.get('title')
    start_time_str = data.get('start_time')
    end_time_str = data.get('end_time')
    category = data.get('category')
    notes = data.get('notes')

    if not all([title, start_time_str, end_time_str, category]):
        return jsonify({'error': 'Missing required fields (title, start_time, end_time, category).'}), 400

    try:
        # Parse and ensure timezone-aware datetimes (UTC)
        start_time = datetime.fromisoformat(start_time_str.replace('Z', '+00:00')).astimezone(pytz.utc)
        end_time = datetime.fromisoformat(end_time_str.replace('Z', '+00:00')).astimezone(pytz.utc)
        
        if start_time >= end_time:
            return jsonify({'error': 'Start time must be before end time.'}), 400
            
    except ValueError:
        return jsonify({'error': 'Invalid date/time format for start_time or end_time. Use ISO 8601.'}), 400

    if current_app.add_schedule(current_user_identity, title, start_time, end_time, category, notes): # Access model func via app proxy
        flash('Schedule created successfully!', 'success') # Flash message for UI feedback if not purely API
        return jsonify({'message': 'Schedule created successfully!'}), 201
    else:
        flash('Failed to create schedule.', 'error')
        return jsonify({'error': 'Failed to create schedule.'}), 500

@main.route('/api/categories', methods=['GET'])
@jwt_required()
def api_get_categories():
    current_user_identity = get_jwt_identity()
    categories = current_app.get_all_categories(current_user_identity) # Access model func via app proxy
    return jsonify(categories)

@main.route('/api/categories', methods=['POST'])
@jwt_required()
def api_add_category():
    current_user_identity = get_jwt_identity()
    data = request.get_json()
    category_name = data.get('category_name')

    if not category_name:
        return jsonify({'error': 'Category name is required.'}), 400

    if current_app.add_category(current_user_identity, category_name): # Access model func via app proxy
        flash(f"Category '{category_name}' added!", 'success')
        return jsonify({'message': f"Category '{category_name}' added successfully."}), 201
    else:
        flash(f"Failed to add category '{category_name}'.", 'error')
        return jsonify({'error': 'Failed to add category.'}), 500

@main.route('/settings')
@jwt_required()
def settings():
    current_user_identity = get_jwt_identity()
    return render_template('settings.html',
                           username=current_user_identity,
                           selected_branch=session.get('selected_branch'),
                           inbox_notifications=dummy_inbox_notifications,
                           show_notifications_button=True)