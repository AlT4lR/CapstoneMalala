# website/views.py

from flask import Blueprint, render_template, request, redirect, url_for, session, flash, make_response, current_app, send_from_directory, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity, verify_jwt_in_request
from datetime import datetime
import os

from .forms import TransactionForm
from .models import get_transactions_by_status, get_analytics_data
import logging

logger = logging.getLogger(__name__)
main = Blueprint('main', __name__)

@main.route('/sw.js')
def service_worker():
    return send_from_directory('static', 'sw.js', mimetype='application/javascript')

# --- Main Navigation Routes ---
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

@main.route('/dashboard')
@jwt_required()
def dashboard():
    if not session.get('selected_branch'):
        return redirect(url_for('main.branches'))
    return render_template('dashboard.html', username=get_jwt_identity(), selected_branch=session.get('selected_branch'), show_sidebar=True)

# --- Transaction Routes ---
@main.route('/transactions')
@jwt_required()
def transactions():
    form = TransactionForm()
    return render_template('transactions.html', show_sidebar=True, form=form)

@main.route('/transactions/pending')
@jwt_required()
def transactions_pending():
    username = get_jwt_identity()
    selected_branch = session.get('selected_branch')
    if not selected_branch: return redirect(url_for('main.branches'))
    
    transactions = get_transactions_by_status(username, selected_branch, 'Pending')
    form = TransactionForm()
    
    return render_template('pending_transactions.html', 
                           transactions=transactions, form=form, show_sidebar=True)

@main.route('/transactions/paid')
@jwt_required()
def transactions_paid():
    username = get_jwt_identity()
    selected_branch = session.get('selected_branch')
    if not selected_branch: return redirect(url_for('main.branches'))
    
    transactions = get_transactions_by_status(username, selected_branch, 'Paid')
    form = TransactionForm()

    return render_template('paid_transactions.html', 
                           transactions=transactions, form=form, show_sidebar=True)

@main.route('/add-transaction', methods=['POST'])
@jwt_required()
def add_transaction():
    username = get_jwt_identity()
    selected_branch = session.get('selected_branch')
    form = TransactionForm()
    
    redirect_url = url_for('main.transactions_pending') # Default
    if request.referrer and 'paid' in request.referrer:
        redirect_url = url_for('main.transactions_paid')
    elif request.referrer and 'transactions' in request.referrer:
        redirect_url = url_for('main.transactions_pending')

    if form.validate_on_submit():
        if current_app.add_transaction(username, selected_branch, form.data):
            flash('Successfully added a new transaction!', 'success')
        else:
            flash('An error occurred.', 'error')
    else:
        for field, errors in form.errors.items():
            flash(f"Error in {getattr(form, field).label.text}: {errors[0]}", "error")
                
    return redirect(redirect_url)

# --- Other Main Routes ---
@main.route('/analytics')
@jwt_required()
def analytics():
    analytics_data = get_analytics_data(get_jwt_identity(), datetime.now().year)
    return render_template('analytics.html', analytics_data=analytics_data, show_sidebar=True)

@main.route('/invoice')
@jwt_required()
def invoice():
    return render_template('invoice.html', show_sidebar=True)

# --- THIS IS THE FIX: Added Missing Routes ---
@main.route('/billings')
@jwt_required()
def billings():
    # Placeholder: Renders a simple page for now.
    return render_template('billings.html', show_sidebar=True)

@main.route('/schedules')
@jwt_required()
def schedules():
    # Placeholder: Renders a simple page for now.
    return render_template('schedules.html', show_sidebar=True)

@main.route('/settings')
@jwt_required()
def settings():
    # Placeholder: Renders a simple page for now.
    return render_template('settings.html', show_sidebar=True)
# --- End of Fix ---

# --- API Routes ---
@main.route('/api/transactions/<transaction_id>', methods=['DELETE'])
@jwt_required()
def delete_transaction_route(transaction_id):
    if current_app.delete_transaction(get_jwt_identity(), transaction_id):
        flash('Successfully deleted a Transaction!', 'success')
        return jsonify({'success': True}), 200
    return jsonify({'error': 'Failed to delete transaction.'}), 404