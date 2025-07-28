# website/views.py

from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from flask_jwt_extended import jwt_required, get_jwt_identity # ADDED: JWT imports

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
    {'id': '#368912', 'name': 'Jessilyn Telma', 'date': '06/12/2025', 'time': '02:15 PM', 'amount': 20000.00, 'method': 'Bank-to-Bank', 'status': 'Paid', 'notes': 'Invoice #INV-2025-06-01'}
]

dummy_inbox_notifications = [
    {'id': 1, 'name': 'Security Bank', 'preview': 'Bill for the week Dear valued customerh', 'date': '30 May 2025, 2:00 PM', 'icon': 'security_bank_icon.png'},
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
        {'value': 'P 1,000,000', 'percentage': 95, 'color': '#ff00ff'},
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
@jwt_required() # ADDED: Protect with JWT
def branches():
    current_user_identity = get_jwt_identity() # ADDED: Get user identity from JWT
    from_dashboard = 'selected_branch' in session and session['selected_branch'] is not None
    return render_template('branches.html', 
                           username=current_user_identity, # Use JWT identity
                           branches=BRANCH_CATEGORIES,
                           from_dashboard=from_dashboard)


@main.route('/select_branch/<branch_name>')
@jwt_required() # ADDED: Protect with JWT
def select_branch(branch_name):
    # User is authenticated by JWT; store branch selection in session (if it's per-session)
    # Or, if branch selection needs to persist, it should be stored in the user model in DB
    session['selected_branch'] = branch_name 
    return redirect(url_for('main.dashboard'))


@main.route('/')
@main.route('/dashboard')
@jwt_required() # ADDED: Protect with JWT
def dashboard():
    current_user_identity = get_jwt_identity() # ADDED: Get user identity from JWT
    return render_template('dashboard.html',
                           username=current_user_identity, # Use JWT identity
                           selected_branch=session.get('selected_branch'),
                           inbox_notifications=dummy_inbox_notifications,
                           chart_data=budget_chart_data,
                           branches=BRANCH_CATEGORIES)


@main.route('/transactions')
@jwt_required() # ADDED: Protect with JWT
def transactions():
    current_user_identity = get_jwt_identity() # ADDED: Get user identity from JWT
    return render_template('transactions.html',
                           username=current_user_identity, # Use JWT identity
                           selected_branch=session.get('selected_branch'),
                           transactions=transactions_data,
                           inbox_notifications=dummy_inbox_notifications)


@main.route('/add-transaction', methods=['GET', 'POST'])
@jwt_required() # ADDED: Protect with JWT
def add_transaction():
    current_user_identity = get_jwt_identity() # ADDED: Get user identity from JWT
    if request.method == 'POST':
        # Here you would process the form data (e.g., save to MongoDB)
        name = request.form.get('name')
        transaction_id = request.form.get('transaction_id')
        date_time = request.form.get('date_time')
        amount = request.form.get('amount')
        payment_method = request.form.get('payment_method')
        status = request.form.get('status')

        # Dummy success message for demonstration
        flash('Successfully Added a Transaction!', 'success')
        # You might want to redirect after a successful add to prevent re-submission
        return redirect(url_for('main.add_transaction'))

    return render_template('add_transaction.html',
                           username=current_user_identity, # Use JWT identity
                           inbox_notifications=dummy_inbox_notifications)


@main.route('/archive')
@jwt_required() # ADDED: Protect with JWT
def archive():
    current_user_identity = get_jwt_identity() # ADDED: Get user identity from JWT
    return render_template('_archive.html',
                           username=current_user_identity, # Use JWT identity
                           selected_branch=session.get('selected_branch'),
                           archived_items=archived_items_data,
                           inbox_notifications=dummy_inbox_notifications)


@main.route('/billings')
@jwt_required() # ADDED: Protect with JWT
def wallet():
    current_user_identity = get_jwt_identity() # ADDED: Get user identity from JWT
    return render_template('billings.html',
                           username=current_user_identity, # Use JWT identity
                           selected_branch=session.get('selected_branch'),
                           inbox_notifications=dummy_inbox_notifications)


@main.route('/analytics')
@jwt_required() # ADDED: Protect with JWT
def analytics():
    current_user_identity = get_jwt_identity() # ADDED: Get user identity from JWT
    return render_template('analytics.html',
                           username=current_user_identity, # Use JWT identity
                           selected_branch=session.get('selected_branch'),
                           revenue_data=analytics_revenue_data,
                           suppliers=analytics_supplier_data,
                           inbox_notifications=dummy_inbox_notifications)


@main.route('/notifications')
@jwt_required() # ADDED: Protect with JWT
def notifications():
    current_user_identity = get_jwt_identity() # ADDED: Get user identity from JWT
    return render_template('notifications.html',
                           username=current_user_identity, # Use JWT identity
                           selected_branch=session.get('selected_branch'),
                           inbox_notifications=dummy_inbox_notifications)