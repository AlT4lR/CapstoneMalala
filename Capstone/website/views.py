# website/views.py

from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify, make_response, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity, verify_jwt_in_request
from datetime import datetime, timedelta
import pytz
from flask_babel import gettext as _

from .models import (
    add_category, get_user_by_username, add_user, check_password,
    update_last_login, set_user_otp, verify_user_otp, record_failed_login_attempt,
    add_schedule, get_schedules_by_date_range, get_all_categories
)
from .forms import TransactionForm
import logging
from flask_limiter.util import get_remote_address
from . import limiter

logger = logging.getLogger(__name__)
main = Blueprint('main', __name__)

# ... (all mock data remains the same) ...
BRANCH_CATEGORIES = [
    {'name': 'DOUBLE L', 'icon': 'building_icon.png'}, {'name': 'SUB-URBAN', 'icon': 'building_icon.png'},
    {'name': 'KASIGLAHAN', 'icon': 'building_icon.png'}, {'name': 'SOUTHVILLE 8B', 'icon': 'building_icon.png'},
    {'name': 'SITIO TANAG', 'icon': 'building_icon.png'}
]
dummy_inbox_notifications = [
    {'id': 1, 'name': 'Security Bank', 'preview': 'Bill for the week Dear valued customerh', 'date': '30 May 2025, 2:00 PM', 'icon': 'security_bank_icon.png'},
    {'id': 2, 'name': 'New Message', 'preview': 'You have a new message from support.', 'date': 'July 1, 2025, 1:00 PM', 'icon': 'message_icon.png'},
    {'id': 3, 'name': 'Reminder', 'preview': 'Review pending payments.', 'date': 'July 2, 2025, 9:00 AM', 'icon': 'reminder_icon.png'},
]
ALL_BRANCH_BUDGET_DATA = {
    'DOUBLE L': [{'label': 'Income', 'value': 40, 'color': '#facc15'}, {'label': 'Spent', 'value': 20, 'color': '#a855f7'}, {'label': 'Savings', 'value': 30, 'color': '#ec4899'}, {'label': 'Scheduled', 'value': 10, 'color': '#3b82f6'}],
}
archived_items_data = [
    {'name': 'Nenia Ann Valenzuela', 'id': '#246810', 'datetime': '2025-07-01T10:30:00', 'relative_time': '45 minutes ago'},
    {'name': 'Jessilyn Telma', 'id': '#368912', 'datetime': '2025-07-01T10:30:00', 'relative_time': '45 minutes ago'}
]
analytics_revenue_data = {'month': 'MAY 2025', 'labels': ['Week 1', 'Week 2', 'Week 3', 'Week 4', 'Week 5'], 'data': []}
analytics_supplier_data = []

# --- Helper Function ---
# ... (get_week_start_date_utc remains the same) ...
def get_week_start_date_utc(date_obj):
    if date_obj.tzinfo is None:
        date_obj = date_obj.replace(tzinfo=pytz.utc)
    days_to_subtract = (date_obj.weekday() + 1) % 7
    return (date_obj - timedelta(days=days_to_subtract)).replace(hour=0, minute=0, second=0, microsecond=0)

# --- Routes ---
# ... (all routes from '/' up to settings remain unchanged) ...
@main.route('/')
def root_route():
    try:
        verify_jwt_in_request()
        if session.get('selected_branch'):
            return redirect(url_for('main.dashboard'))
        else:
            return redirect(url_for('main.branches'))
    except Exception:
        return redirect(url_for('auth.login'))

@main.route('/branches')
@jwt_required()
def branches():
    return render_template('branches.html',
                           username=get_jwt_identity(),
                           available_branches=BRANCH_CATEGORIES,
                           show_sidebar=False,
                           show_notifications_button=True,
                           inbox_notifications=dummy_inbox_notifications)

@main.route('/select_branch/<branch_name>')
@jwt_required()
def select_branch(branch_name):
    session['selected_branch'] = branch_name
    return redirect(url_for('main.dashboard'))

@main.route('/dashboard')
@jwt_required()
def dashboard():
    selected_branch = session.get('selected_branch')
    if not selected_branch:
        flash("Please select a branch first.", "info")
        return redirect(url_for('main.branches'))
    return render_template('dashboard.html',
                           username=get_jwt_identity(),
                           selected_branch=selected_branch,
                           chart_data=ALL_BRANCH_BUDGET_DATA.get(selected_branch, {}),
                           show_sidebar=True,
                           show_notifications_button=True,
                           inbox_notifications=dummy_inbox_notifications)

@main.route('/transactions/paid')
@jwt_required()
def transactions_paid():
    selected_branch = session.get('selected_branch')
    if not selected_branch:
        flash("Please select a branch to view transactions.", "info")
        return redirect(url_for('main.branches'))
    paid_transactions = current_app.get_transactions_by_status(get_jwt_identity(), selected_branch, 'Paid')
    return render_template('paid_transactions.html',
                           username=get_jwt_identity(),
                           selected_branch=selected_branch,
                           transactions=paid_transactions,
                           current_filter='paid',
                           show_sidebar=True,
                           show_notifications_button=True,
                           inbox_notifications=dummy_inbox_notifications)

@main.route('/transactions/pending')
@jwt_required()
def transactions_pending():
    selected_branch = session.get('selected_branch')
    if not selected_branch:
        flash("Please select a branch to view transactions.", "info")
        return redirect(url_for('main.branches'))
    pending_transactions = current_app.get_transactions_by_status(get_jwt_identity(), selected_branch, 'Pending')
    return render_template('pending_transactions.html',
                           username=get_jwt_identity(),
                           selected_branch=selected_branch,
                           transactions=pending_transactions,
                           current_filter='pending',
                           show_sidebar=True,
                           show_notifications_button=True,
                           inbox_notifications=dummy_inbox_notifications)

@main.route('/transactions/declined')
@jwt_required()
def transactions_declined():
    selected_branch = session.get('selected_branch')
    if not selected_branch:
        flash("Please select a branch to view transactions.", "info")
        return redirect(url_for('main.branches'))
    declined_transactions = current_app.get_transactions_by_status(get_jwt_identity(), selected_branch, 'Declined')
    return render_template('declined_transactions.html',
                           username=get_jwt_identity(),
                           selected_branch=selected_branch,
                           transactions=declined_transactions,
                           current_filter='declined',
                           show_sidebar=True,
                           show_notifications_button=True,
                           inbox_notifications=dummy_inbox_notifications)

@main.route('/add-transaction', methods=['GET', 'POST'])
@jwt_required()
def add_transaction():
    current_user_identity = get_jwt_identity()
    selected_branch = session.get('selected_branch')
    form = TransactionForm()

    if not selected_branch:
        flash("Please select a branch before adding a transaction.", "error")
        return redirect(url_for('main.branches'))

    if form.validate_on_submit():
        form_data = {
            'name': request.form.get('name'),
            'transaction_id': request.form.get('transaction_id'),
            'date_time': request.form.get('date_time'),
            'amount': request.form.get('amount'),
            'payment_method': request.form.get('payment_method'),
            'status': request.form.get('status')
        }

        if not all(form_data.values()):
            flash('All transaction fields are required.', 'error')
        else:
            try:
                datetime_naive = datetime.fromisoformat(form_data['date_time'])
                datetime_utc = pytz.utc.localize(datetime_naive)
                new_transaction_data = {
                    'name': form_data['name'],
                    'transaction_id': form_data['transaction_id'],
                    'datetime_utc': datetime_utc,
                    'amount': float(form_data['amount']),
                    'payment_method': form_data['payment_method'],
                    'status': form_data['status']
                }
                if current_app.add_transaction(current_user_identity, selected_branch, new_transaction_data):
                    flash('Successfully Added a Transaction!', 'success')
                    if form_data['status'] == 'Paid':
                        return redirect(url_for('main.transactions_paid'))
                    elif form_data['status'] == 'Pending':
                        return redirect(url_for('main.transactions_pending'))
                    else:
                        return redirect(url_for('main.transactions_declined'))
                else:
                    flash('An error occurred while adding the transaction.', 'error')
            except ValueError:
                flash('Invalid date or amount format.', 'error')

        return render_template('add_transaction.html',
                               username=current_user_identity,
                               selected_branch=selected_branch,
                               inbox_notifications=dummy_inbox_notifications,
                               show_sidebar=True,
                               show_notifications_button=True,
                               form=form,
                               transaction_data=form_data)

    return render_template('add_transaction.html',
                           username=current_user_identity,
                           selected_branch=selected_branch,
                           inbox_notifications=dummy_inbox_notifications,
                           show_sidebar=True,
                           show_notifications_button=True,
                           form=form)

@main.route('/archive')
@jwt_required()
def archive():
    return render_template('_archive.html',
                           username=get_jwt_identity(),
                           selected_branch=session.get('selected_branch'),
                           archived_items=archived_items_data,
                           inbox_notifications=dummy_inbox_notifications,
                           show_sidebar=True,
                           show_notifications_button=True)

@main.route('/billings')
@jwt_required()
def wallet():
    return render_template('billings.html',
                           username=get_jwt_identity(),
                           selected_branch=session.get('selected_branch'),
                           inbox_notifications=dummy_inbox_notifications,
                           show_sidebar=True,
                           show_notifications_button=True)

@main.route('/analytics')
@jwt_required()
def analytics():
    selected_branch = session.get('selected_branch')
    if not selected_branch:
        flash("Please select a branch to view analytics.", "info")
        return redirect(url_for('main.branches'))
    return render_template('analytics.html',
                           username=get_jwt_identity(),
                           selected_branch=selected_branch,
                           revenue_data=analytics_revenue_data,
                           suppliers=analytics_supplier_data,
                           inbox_notifications=dummy_inbox_notifications,
                           show_sidebar=True,
                           show_notifications_button=True)

@main.route('/notifications')
@jwt_required()
def notifications():
    return render_template('notifications.html',
                           username=get_jwt_identity(),
                           selected_branch=session.get('selected_branch'),
                           inbox_notifications=dummy_inbox_notifications,
                           show_sidebar=True,
                           show_notifications_button=True)

@main.route('/invoice')
@jwt_required()
def invoice():
    return render_template('invoice.html',
                           username=get_jwt_identity(),
                           selected_branch=session.get('selected_branch'),
                           inbox_notifications=dummy_inbox_notifications,
                           show_sidebar=True,
                           show_notifications_button=True)

@main.route('/schedules', methods=['GET'])
@jwt_required()
def schedules():
    current_user_identity = get_jwt_identity()
    selected_branch = session.get('selected_branch')
    if not selected_branch:
        flash("Please select a branch to view schedules.", "info")
        return redirect(url_for('main.branches'))
    categories = current_app.get_all_categories(current_user_identity)
    today_utc = datetime.now(pytz.utc)
    try:
        current_date_utc = datetime(
            request.args.get('year', today_utc.year, type=int),
            request.args.get('month', today_utc.month, type=int),
            request.args.get('day', today_utc.day, type=int),
            tzinfo=pytz.utc
        )
    except ValueError:
        flash("Invalid date parameters.", "error")
        current_date_utc = today_utc
    mini_cal_start_date = get_week_start_date_utc(current_date_utc)
    return render_template('schedules.html',
                           username=current_user_identity,
                           selected_branch=selected_branch,
                           inbox_notifications=dummy_inbox_notifications,
                           show_sidebar=True,
                           show_notifications_button=True,
                           FLASK_INITIAL_DATE_ISO=current_date_utc.isoformat(),
                           categories=categories,
                           mini_cal_start_date=mini_cal_start_date)

@main.route('/settings')
@jwt_required()
def settings():
    return render_template('settings.html',
                           username=get_jwt_identity(),
                           selected_branch=session.get('selected_branch'),
                           inbox_notifications=dummy_inbox_notifications,
                           show_sidebar=True,
                           show_notifications_button=True)

# --- API and PWA Routes ---
@main.route('/api/transaction/<transaction_id>', methods=['GET'])
@jwt_required()
def get_transaction_details(transaction_id):
    username = get_jwt_identity()
    transaction = current_app.get_transaction_by_id(username, transaction_id)
    if transaction:
        return jsonify(transaction), 200
    else:
        return jsonify({'error': 'Transaction not found or permission denied.'}), 404

@main.route('/api/transactions/<transaction_id>', methods=['DELETE'])
@jwt_required()
def delete_transaction_route(transaction_id):
    username = get_jwt_identity()
    if current_app.delete_transaction(username, transaction_id):
        return jsonify({'success': True, 'message': 'Transaction deleted successfully.'}), 200
    else:
        return jsonify({'error': 'Failed to delete transaction or permission denied.'}), 404

@main.route('/offline')
def offline():
    return render_template('offline.html')