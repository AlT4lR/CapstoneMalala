# website/views/billings.py

from flask import render_template, request, jsonify, session
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime

from . import main # Import the blueprint
from ..forms import LoanForm
from ..models import log_user_activity, get_loans, add_loan, get_weekly_billing_summary

@main.route('/billings')
@jwt_required()
def billings():
    username = get_jwt_identity()
    selected_branch = session.get('selected_branch')
    form = LoanForm()
    loans = get_loans(username, selected_branch)
    # Sort by date issued, most recent first, to ensure a consistent order
    loans.sort(key=lambda l: l['date_issued'] or datetime.min, reverse=True)
    return render_template('billings.html', show_sidebar=True, form=form, loans=loans)

# --- Billings & Loans API Routes ---
@main.route('/api/billings/summary', methods=['GET'])
@jwt_required()
def get_billings_summary():
    username = get_jwt_identity()
    # --- START OF MODIFICATION: Get selected branch from session ---
    selected_branch = session.get('selected_branch')
    # --- END OF MODIFICATION ---
    try:
        year = int(request.args.get('year'))
        week = int(request.args.get('week'))
    except (TypeError, ValueError):
        return jsonify({'error': 'Invalid year or week parameter'}), 400

    # --- START OF MODIFICATION: Pass selected_branch to the model function ---
    summary_data = get_weekly_billing_summary(username, selected_branch, year, week)
    # --- END OF MODIFICATION ---
    return jsonify(summary_data)

@main.route('/api/loans/add', methods=['POST'])
@jwt_required()
def add_loan_route():
    username = get_jwt_identity()
    selected_branch = session.get('selected_branch')
    form = LoanForm()
    if form.validate_on_submit():
        if add_loan(username, selected_branch, form.data):
            log_user_activity(username, 'Added a new loan')
            return jsonify({'success': True})
    return jsonify({'success': False, 'errors': form.errors}), 400