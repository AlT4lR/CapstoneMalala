# website/views.py

from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime, timedelta
from .models import (
    get_user_by_username, add_user, check_password, update_last_login,
    set_user_otp, verify_user_otp, record_failed_login_attempt,
    add_schedule, get_schedules_by_date_range, get_all_categories
)

main = Blueprint('main', __name__)

# --- Static Data Definitions (NOW Branch-Aware) ---
BRANCH_CATEGORIES = [
    {'name': 'DOUBLE L', 'icon': 'building_icon.png'},
    {'name': 'SUB-URBAN', 'icon': 'building_icon.png'},
    {'name': 'KASIGLAHAN', 'icon': 'building_icon.png'},
    {'name': 'SOUTHVILLE 8B', 'icon': 'building_icon.png'},
    {'name': 'SITIO TANAG', 'icon': 'building_icon.png'}
]

# Modified transactions_data to include 'branch'
transactions_data = [
    {'id': '#123456', 'name': 'Jody Sta. Maria', 'date': '05/30/2025', 'time': '10:30 AM', 'amount': 999.00, 'method': 'Bank-to-Bank', 'status': 'Pending', 'notes': 'Initial deposit.', 'branch': 'DOUBLE L'},
    {'id': '#246810', 'name': 'Nenia Ann Valenzuela', 'date': '05/30/2025', 'time': '11:49 AM', 'amount': 10000.00, 'method': 'Bank-to-Bank', 'status': 'Paid', 'notes': 'Payment for design services.', 'branch': 'DOUBLE L'},
    {'id': '#368912', 'name': 'Jessilyn Telma', 'date': '06/12/2025', 'time': '02:15 PM', 'amount': 20000.00, 'method': 'Bank-to-Bank', 'status': 'Paid', 'notes': 'Invoice #INV-2025-06-01', 'branch': 'SUB-URBAN'},
    {'id': '#481216', 'name': 'Shuvee Entrata', 'date': '06/17/2025', 'time': '09:00 AM', 'amount': 2000.00, 'method': 'Bank-to-Bank', 'status': 'Pending', 'notes': 'Service fee.', 'branch': 'SUB-URBAN'},
    {'id': '#5101520', 'name': 'Will Ashley', 'date': '07/1/2025', 'time': '03:45 PM', 'amount': 80000.00, 'method': 'Bank-to-Bank', 'status': 'Pending', 'notes': 'Project completion payment.', 'branch': 'KASIGLAHAN'},
    {'id': '#6121824', 'name': 'Brent Manalo', 'date': '07/1/2025', 'time': '04:00 PM', 'amount': 80000.00, 'method': 'Bank-to-Bank', 'status': 'Pending', 'notes': 'New Project Payment.', 'branch': 'SOUTHVILLE 8B'},
    {'id': '#6121825', 'name': 'Charlie Fleming', 'date': '07/1/2025', 'time': '04:30 PM', 'amount': 80000.00, 'method': 'Bank-to-Bank', 'status': 'Pending', 'notes': 'Consultation Fee.', 'branch': 'SITIO TANAG'},
    {'id': '#7000000', 'name': 'Alice Smith', 'date': '07/02/2025', 'time': '10:00 AM', 'amount': 5000.00, 'method': 'Cash', 'status': 'Paid', 'notes': 'Consultation.', 'branch': 'DOUBLE L'},
    # Add more data for other branches if needed for demonstration
]

dummy_inbox_notifications = [
    {'id': 1, 'name': 'Security Bank', 'preview': 'Bill for the week Dear valued customerh', 'date': '30 May 2025, 2:00 PM', 'icon': 'security_bank_icon.png'},
    {'id': 2, 'name': 'New Message', 'preview': 'You have a new message from support.', 'date': 'July 1, 2025, 1:00 PM', 'icon': 'message_icon.png'},
    {'id': 3, 'name': 'Reminder', 'preview': 'Review pending payments.', 'date': 'July 2, 2025, 9:00 AM', 'icon': 'reminder_icon.png'},
]

# Separate budget data for each branch (or a default for "All Branches")
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
    'DEFAULT': [ # Data for when no specific branch is selected or matches
        { 'label': 'Income', 'value': 10, 'color': '#facc15' },
        { 'label': 'Spent', 'value': 20, 'color': '#a855f7' },
        { 'label': 'Savings', 'value': 30, 'color': '#ec4899' },
        { 'label': 'Scheduled', 'value': 40, 'color': '#3b82f6' }
    ]
}


archived_items_data = [
    {'name': 'Nenia Ann Valenzuela', 'id': '#246810', 'datetime': '07/01/2025, 10:30AM', 'relative_time': '45 minutes ago'},
    {'name': 'Jessilyn Telma', 'id': '#368912', 'datetime': '07/01/2025, 10:30AM', 'relative_time': '45 minutes ago'}
]

analytics_revenue_data = {
    'month': 'MAY 2025',
    'labels': ['Week 1', 'Week 2', 'Week 3', 'Week 4', 'Week 5'],
    'legend': [
        {'label': 'P 100,000', 'color': '#ff0000'},
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

analytics_supplier_data = [
    {'name': 'Vincent Lee', 'score': 89, 'delivery': 96, 'defects': 1.2, 'variance': 2.1, 'lead_time': 5.2},
    {'name': 'Anthony Lee', 'score': 72, 'delivery': 82, 'defects': 3.5, 'variance': -1.8, 'lead_time': 7.3},
    {'name': 'Vincent Lee', 'score': 89, 'delivery': 96, 'defects': 1.2, 'variance': 2.1, 'lead_time': 5.2},
    {'name': 'Anthony Lee', 'score': 72, 'delivery': 82, 'defects': 3.5, 'variance': -1.8, 'lead_time': 7.3},
]

# --- Route Definitions ---

@main.route('/branches')
@jwt_required()
def branches():
    current_user_identity = get_jwt_identity()
    from_dashboard = 'selected_branch' in session and session['selected_branch'] is not None
    return render_template('branches.html',
                           username=current_user_identity,
                           branches=BRANCH_CATEGORIES,
                           from_dashboard=from_dashboard,
                           inbox_notifications=dummy_inbox_notifications,
                           show_notifications_button=True)


@main.route('/select_branch/<branch_name>')
@jwt_required()
def select_branch(branch_name):
    session['selected_branch'] = branch_name 
    return redirect(url_for('main.dashboard'))


@main.route('/')
@main.route('/dashboard')
@jwt_required()
def dashboard():
    current_user_identity = get_jwt_identity()
    selected_branch = session.get('selected_branch', 'DEFAULT') # Get selected branch, default to 'DEFAULT'
    
    # Retrieve budget data specific to the selected branch, fallback to 'DEFAULT'
    current_budget_data = ALL_BRANCH_BUDGET_DATA.get(selected_branch, ALL_BRANCH_BUDGET_DATA['DEFAULT'])

    return render_template('dashboard.html',
                           username=current_user_identity, 
                           selected_branch=selected_branch,
                           inbox_notifications=dummy_inbox_notifications,
                           chart_data=current_budget_data, # Pass branch-specific data
                           branches=BRANCH_CATEGORIES,
                           show_notifications_button=True)


@main.route('/transactions')
@jwt_required()
def transactions():
    return redirect(url_for('main.transactions_paid'))


@main.route('/transactions/paid')
@jwt_required()
def transactions_paid():
    current_user_identity = get_jwt_identity()
    selected_branch = session.get('selected_branch')

    # Filter transactions based on selected branch
    if selected_branch:
        paid_transactions = [t for t in transactions_data if t['status'] == 'Paid' and t['branch'] == selected_branch]
    else:
        # If no specific branch selected, show all paid transactions (or prompt to select a branch)
        paid_transactions = [t for t in transactions_data if t['status'] == 'Paid']
        flash("Please select a branch to view branch-specific transactions.", "info")
    
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

    # Filter transactions based on selected branch
    if selected_branch:
        pending_transactions = [t for t in transactions_data if t['status'] == 'Pending' and t['branch'] == selected_branch]
    else:
        # If no specific branch selected, show all pending transactions (or prompt to select a branch)
        pending_transactions = [t for t in transactions_data if t['status'] == 'Pending']
        flash("Please select a branch to view branch-specific transactions.", "info")
    
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
    selected_branch = session.get('selected_branch') # Get current branch for new transaction

    if not selected_branch:
        flash("Please select a branch before adding a transaction.", "error")
        return redirect(url_for('main.branches')) # Redirect to branch selection

    if request.method == 'POST':
        name = request.form.get('name')
        transaction_id = request.form.get('transaction_id')
        date_time_str = request.form.get('date_time')
        amount = request.form.get('amount')
        payment_method = request.form.get('payment_method')
        status = request.form.get('status')

        date_part = date_time_str.split('T')[0] if date_time_str else ''
        time_part = datetime.strptime(date_time_str, '%Y-%m-%dT%H:%M').strftime('%I:%M %p') if date_time_str else ''

        transactions_data.append({
            'id': transaction_id,
            'name': name,
            'date': date_part,
            'time': time_part,
            'amount': float(amount),
            'method': payment_method,
            'status': status,
            'notes': 'Added via form.',
            'branch': selected_branch # Associate with the selected branch
        })

        flash('Successfully Added a Transaction!', 'success')
        
        if status == 'Paid':
            return redirect(url_for('main.transactions_paid'))
        elif status == 'Pending':
            return redirect(url_for('main.transactions_pending'))
        else:
            return redirect(url_for('main.transactions_paid'))

    return render_template('add_transaction.html',
                           username=current_user_identity,
                           inbox_notifications=dummy_inbox_notifications,
                           current_filter='add',
                           selected_branch=selected_branch, # Pass selected branch to template
                           show_notifications_button=True)


@main.route('/archive')
@jwt_required()
def archive():
    current_user_identity = get_jwt_identity()
    return render_template('_archive.html',
                           username=current_user_identity,
                           selected_branch=session.get('selected_branch'),
                           archived_items=archived_items_data,
                           inbox_notifications=dummy_inbox_notifications,
                           show_notifications_button=True)


@main.route('/billings')
@jwt_required()
def wallet():
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
    return render_template('analytics.html',
                           username=current_user_identity,
                           selected_branch=session.get('selected_branch'),
                           revenue_data=analytics_revenue_data,
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
    
    # Get all categories for the user
    categories = get_all_categories(current_user_identity)

    # Determine current date based on query parameters or default to today
    year = request.args.get('year', type=int)
    month = request.args.get('month', type=int)
    day = request.args.get('day', type=int)

    today = datetime.now()
    if year and month and day:
        current_date = datetime(year, month, day)
    elif year and month: # Default to first day of month if only year/month
        current_date = datetime(year, month, 1)
    else:
        current_date = today # Default to today if no params

    # For mini-calendar (always month view relative to current_date)
    # The mini_cal_start_date logic helps to ensure the first day displayed is always a Sunday,
    # and includes days from the previous month if necessary to fill the first week.
    first_day_of_month = current_date.replace(day=1)
    mini_cal_start_date = first_day_of_month - timedelta(days=first_day_of_month.weekday() + 1)
    if mini_cal_start_date.weekday() != 6: # Ensure it's truly Sunday (0 is Monday, 6 is Sunday)
        mini_cal_start_date = mini_cal_start_date - timedelta(days=(mini_cal_start_date.weekday() + 1) % 7)


    return render_template('schedules.html',
                           username=current_user_identity,
                           selected_branch=session.get('selected_branch'),
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
        # Ensure 'Z' is handled for UTC. fromisoformat handles +HH:MM but not Z directly.
        # So we replace 'Z' with '+00:00' for full compatibility.
        start_date = datetime.fromisoformat(start_date_str.replace('Z', '+00:00'))
        end_date = datetime.fromisoformat(end_date_str.replace('Z', '+00:00'))
    except ValueError:
        return jsonify({'error': 'Invalid date format. Use ISO 8601 (YYYY-MM-DDTHH:MM:SS.sssZ).'}), 400

    schedules = get_schedules_by_date_range(current_user_identity, start_date, end_date)
    
    # Format datetimes to ISO 8601 strings for JSON serialization
    for schedule in schedules:
        schedule['start_time'] = schedule['start_time'].isoformat()
        schedule['end_time'] = schedule['end_time'].isoformat()
        # Optionally remove sensitive or unnecessary fields for client-side
        # if 'createdAt' in schedule: del schedule['createdAt']
        # if 'updatedAt' in schedule: del schedule['updatedAt']

    return jsonify(schedules)

@main.route('/api/schedules', methods=['POST'])
@jwt_required()
def api_create_schedule():
    current_user_identity = get_jwt_identity()
    data = request.get_json()

    if not data:
        return jsonify({'error': 'No data provided.'}), 400

    title = data.get('title')
    start_time_str = data.get('start_time')
    end_time_str = data.get('end_time')
    category = data.get('category')
    notes = data.get('notes')

    if not all([title, start_time_str, end_time_str, category]):
        return jsonify({'error': 'Missing required fields (title, start_time, end_time, category).'}), 400

    try:
        start_time = datetime.fromisoformat(start_time_str.replace('Z', '+00:00'))
        end_time = datetime.fromisoformat(end_time_str.replace('Z', '+00:00'))
    except ValueError:
        return jsonify({'error': 'Invalid date/time format for start_time or end_time. Use ISO 8601.'}), 400

    if add_schedule(current_user_identity, title, start_time, end_time, category, notes):
        flash('Schedule created successfully!', 'success')
        return jsonify({'message': 'Schedule created successfully!'}), 201
    else:
        flash('Failed to create schedule.', 'error')
        return jsonify({'error': 'Failed to create schedule.'}), 500

@main.route('/api/categories', methods=['GET'])
@jwt_required()
def api_get_categories():
    current_user_identity = get_jwt_identity()
    categories = get_all_categories(current_user_identity)
    return jsonify(categories)

@main.route('/api/categories', methods=['POST'])
@jwt_required()
def api_add_category():
    current_user_identity = get_jwt_identity()
    data = request.get_json()
    category_name = data.get('category_name')

    if not category_name:
        return jsonify({'error': 'Category name is required.'}), 400

    # In a real app, you'd want to save this category persistently,
    # for example, in a 'categories' collection, or as part of the user's document.
    # For this example, add_category in models.py just prints and always returns True.
    if add_category(current_user_identity, category_name):
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