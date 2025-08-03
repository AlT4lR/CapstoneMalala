# website/views.py

from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from flask_jwt_extended import jwt_required, get_jwt_identity

main = Blueprint('main', __name__)

# --- Static Data Definitions ---
BRANCH_CATEGORIES = [
    {'name': 'DOUBLE L', 'icon': 'building_icon.png'},
    {'name': 'SUB-URBAN', 'icon': 'building_icon.png'},
    {'name': 'KASIGLAHAN', 'icon': 'building_icon.png'},
    {'name': 'SOUTHVILLE 8B', 'icon': 'building_icon.png'},
    {'name': 'SITIO TANAG', 'icon': 'building_icon.png'}
]

transactions_data = [
    {'id': '#123456', 'name': 'Jody Sta. Maria', 'date': '05/30/2025', 'time': '10:30 AM', 'amount': 999.00, 'method': 'Bank-to-Bank', 'status': 'Pending', 'notes': 'Initial deposit.'},
    {'id': '#246810', 'name': 'Nenia Ann Valenzuela', 'date': '05/30/2025', 'time': '11:49 AM', 'amount': 10000.00, 'method': 'Bank-to-Bank', 'status': 'Paid', 'notes': 'Payment for design services.'},
    {'id': '#368912', 'name': 'Jessilyn Telma', 'date': '06/12/2025', 'time': '02:15 PM', 'amount': 20000.00, 'method': 'Bank-to-Bank', 'status': 'Paid', 'notes': 'Invoice #INV-2025-06-01'},
    {'id': '#481216', 'name': 'Shuvee Entrata', 'date': '06/17/2025', 'time': '09:00 AM', 'amount': 2000.00, 'method': 'Bank-to-Bank', 'status': 'Pending', 'notes': 'Service fee.'},
    {'id': '#5101520', 'name': 'Will Ashley', 'date': '07/1/2025', 'time': '03:45 PM', 'amount': 80000.00, 'method': 'Bank-to-Bank', 'status': 'Pending', 'notes': 'Project completion payment.'},
    {'id': '#6121824', 'name': 'Brent Manalo', 'date': '07/1/2025', 'time': '04:00 PM', 'amount': 80000.00, 'method': 'Bank-to-Bank', 'status': 'Pending', 'notes': 'New Project Payment.'},
    {'id': '#6121825', 'name': 'Charlie Fleming', 'date': '07/1/2025', 'time': '04:30 PM', 'amount': 80000.00, 'method': 'Bank-to-Bank', 'status': 'Pending', 'notes': 'Consultation Fee.'},
    {'id': '#7000000', 'name': 'Alice Smith', 'date': '07/02/2025', 'time': '10:00 AM', 'amount': 5000.00, 'method': 'Cash', 'status': 'Paid', 'notes': 'Consultation.'},
]

dummy_inbox_notifications = [
    {'id': 1, 'name': 'Security Bank', 'preview': 'Bill for the week Dear valued customerh', 'date': '30 May 2025, 2:00 PM', 'icon': 'security_bank_icon.png'},
    {'id': 2, 'name': 'New Message', 'preview': 'You have a new message from support.', 'date': 'July 1, 2025, 1:00 PM', 'icon': 'message_icon.png'},
    {'id': 3, 'name': 'Reminder', 'preview': 'Review pending payments.', 'date': 'July 2, 2025, 9:00 AM', 'icon': 'reminder_icon.png'},
    # Added more dummy notifications for the count
]

budget_chart_data = [
    { 'label': 'Income', 'value': 10, 'color': '#facc15' },
    { 'label': 'Spent', 'value': 20, 'color': '#a855f7' },
    { 'label': 'Savings', 'value': 30, 'color': '#ec4899' },
    { 'label': 'Scheduled', 'value': 40, 'color': '#3b82f6' }
]

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
                           from_dashboard=from_dashboard)


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
    return render_template('dashboard.html',
                           username=current_user_identity, 
                           selected_branch=session.get('selected_branch'),
                           inbox_notifications=dummy_inbox_notifications,
                           chart_data=budget_chart_data,
                           branches=BRANCH_CATEGORIES)


@main.route('/transactions')
@jwt_required()
def transactions():
    return redirect(url_for('main.transactions_paid'))


@main.route('/transactions/paid')
@jwt_required()
def transactions_paid():
    current_user_identity = get_jwt_identity()
    paid_transactions = [t for t in transactions_data if t['status'] == 'Paid']
    
    return render_template('paid_transactions.html',
                           username=current_user_identity,
                           selected_branch=session.get('selected_branch'),
                           transactions=paid_transactions,
                           inbox_notifications=dummy_inbox_notifications,
                           current_filter='paid')


@main.route('/transactions/pending')
@jwt_required()
def transactions_pending():
    current_user_identity = get_jwt_identity()
    pending_transactions = [t for t in transactions_data if t['status'] == 'Pending']
    
    return render_template('pending_transactions.html',
                           username=current_user_identity,
                           selected_branch=session.get('selected_branch'),
                           transactions=pending_transactions,
                           inbox_notifications=dummy_inbox_notifications,
                           current_filter='pending')


@main.route('/add-transaction', methods=['GET', 'POST'])
@jwt_required()
def add_transaction():
    current_user_identity = get_jwt_identity()
    if request.method == 'POST':
        name = request.form.get('name')
        transaction_id = request.form.get('transaction_id')
        date_time = request.form.get('date_time')
        amount = request.form.get('amount')
        payment_method = request.form.get('payment_method')
        status = request.form.get('status')

        transactions_data.append({
            'id': transaction_id,
            'name': name,
            'date': date_time.split('T')[0] if date_time else '',
            'time': date_time.split('T')[1] if date_time else '',
            'amount': float(amount),
            'method': payment_method,
            'status': status,
            'notes': 'Added via form.'
        })

        flash('Successfully Added a Transaction!', 'success')
        
        if status == 'Paid':
            return redirect(url_for('main.transactions_paid'))
        elif status == 'Pending':
            return redirect(url_for('main.transactions_pending'))
        else:
            return redirect(url_for('main.transactions_paid')) # Default redirect

    return render_template('add_transaction.html',
                           username=current_user_identity,
                           inbox_notifications=dummy_inbox_notifications,
                           current_filter='add')


@main.route('/archive')
@jwt_required()
def archive():
    current_user_identity = get_jwt_identity()
    return render_template('_archive.html',
                           username=current_user_identity,
                           selected_branch=session.get('selected_branch'),
                           archived_items=archived_items_data,
                           inbox_notifications=dummy_inbox_notifications)


@main.route('/billings')
@jwt_required()
def wallet():
    current_user_identity = get_jwt_identity()
    return render_template('billings.html',
                           username=current_user_identity,
                           selected_branch=session.get('selected_branch'),
                           inbox_notifications=dummy_inbox_notifications)


@main.route('/analytics')
@jwt_required()
def analytics():
    current_user_identity = get_jwt_identity()
    return render_template('analytics.html',
                           username=current_user_identity,
                           selected_branch=session.get('selected_branch'),
                           revenue_data=analytics_revenue_data,
                           suppliers=analytics_supplier_data,
                           inbox_notifications=dummy_inbox_notifications)


@main.route('/notifications')
@jwt_required()
def notifications():
    current_user_identity = get_jwt_identity()
    return render_template('notifications.html',
                           username=current_user_identity,
                           selected_branch=session.get('selected_branch'),
                           inbox_notifications=dummy_inbox_notifications)


# ADDED: Placeholder routes for new sidebar items
@main.route('/invoice')
@jwt_required()
def invoice():
    current_user_identity = get_jwt_identity()
    return render_template('invoice.html',
                           username=current_user_identity,
                           selected_branch=session.get('selected_branch'),
                           inbox_notifications=dummy_inbox_notifications)

@main.route('/schedules')
@jwt_required()
def schedules():
    current_user_identity = get_jwt_identity()
    return render_template('schedules.html',
                           username=current_user_identity,
                           selected_branch=session.get('selected_branch'),
                           inbox_notifications=dummy_inbox_notifications)

@main.route('/settings')
@jwt_required()
def settings():
    current_user_identity = get_jwt_identity()
    return render_template('settings.html',
                           username=current_user_identity,
                           selected_branch=session.get('selected_branch'),
                           inbox_notifications=dummy_inbox_notifications)