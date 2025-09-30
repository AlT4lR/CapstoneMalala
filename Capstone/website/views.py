from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify, make_response, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity, verify_jwt_in_request
from datetime import datetime
import pytz
import os
from werkzeug.utils import secure_filename

from .forms import TransactionForm
import logging

logger = logging.getLogger(__name__)
main = Blueprint('main', __name__)

# Mock data remains the same...
BRANCH_CATEGORIES = [
    {'name': 'DOUBLE L', 'icon': 'building_icon.png'}, {'name': 'SUB-URBAN', 'icon': 'building_icon.png'},
    {'name': 'KASIGLAHAN', 'icon': 'building_icon.png'}, {'name': 'SOUTHVILLE 8B', 'icon': 'building_icon.png'},
    {'name': 'SITIO TANAG', 'icon': 'building_icon.png'}
]
archived_items_data = [
    {'name': 'Nenia Ann Valenzuela', 'id': '#246810', 'datetime': '2025-07-01T10:30:00', 'relative_time': '45 minutes ago'},
    {'name': 'Jessilyn Telma', 'id': '#368912', 'datetime': '2025-07-01T10:30:00', 'relative_time': '45 minutes ago'}
]
analytics_revenue_data = {
    'month': 'MAY 2025', 
    'labels': ['Week 1', 'Week 2', 'Week 3', 'Week 4', 'Week 5'], 
    'data': [],
    'legend': [] # Added for completeness
}
analytics_supplier_data = []

# --- Helper Functions ---
def get_category_color(category):
    """Helper to map category names to colors for the calendar."""
    colors = {
        'Office': '#5c8374', 'Meetings': '#e91e63', 'Events': '#ef4444',
        'Personal': '#3b82f6', 'Others': '#6b7280'
    }
    return colors.get(category, '#6b7280')

# --- Routes ---
@main.route('/')
def root_route():
    try:
        verify_jwt_in_request(optional=True)
        if get_jwt_identity():
            if session.get('selected_branch'):
                return redirect(url_for('main.dashboard'))
            else:
                return redirect(url_for('main.branches'))
        else:
            return redirect(url_for('auth.login'))
    except Exception:
        return redirect(url_for('auth.login'))

@main.route('/branches')
@jwt_required()
def branches():
    return render_template('branches.html', username=get_jwt_identity(), available_branches=BRANCH_CATEGORIES)

@main.route('/select_branch/<branch_name>')
@jwt_required()
def select_branch(branch_name):
    if branch_name.upper() in [b['name'] for b in [{'name': 'MONTALBAN'}, {'name': 'LAGUNA'}]]: # Basic validation
        session['selected_branch'] = branch_name.upper()
    return redirect(url_for('main.dashboard'))

@main.route('/dashboard')
@jwt_required()
def dashboard():
    selected_branch = session.get('selected_branch')
    if not selected_branch:
        flash("Please select a branch first.", "info")
        return redirect(url_for('main.branches'))
    return render_template('dashboard.html', username=get_jwt_identity(), selected_branch=selected_branch,
                            show_sidebar=True, show_notifications_button=True, archived_items=archived_items_data)

@main.route('/transactions/paid')
@jwt_required()
def transactions_paid():
    selected_branch = session.get('selected_branch')
    if not selected_branch: return redirect(url_for('main.branches'))
    paid_transactions = current_app.get_transactions_by_status(get_jwt_identity(), selected_branch, 'Paid')
    return render_template('paid_transactions.html', username=get_jwt_identity(), selected_branch=selected_branch,
                            transactions=paid_transactions, show_sidebar=True, show_notifications_button=True)

@main.route('/transactions/pending')
@jwt_required()
def transactions_pending():
    selected_branch = session.get('selected_branch')
    if not selected_branch: return redirect(url_for('main.branches'))
    pending_transactions = current_app.get_transactions_by_status(get_jwt_identity(), selected_branch, 'Pending')
    return render_template('pending_transactions.html', username=get_jwt_identity(), selected_branch=selected_branch,
                            transactions=pending_transactions, show_sidebar=True, show_notifications_button=True)

@main.route('/transactions/declined')
@jwt_required()
def transactions_declined():
    selected_branch = session.get('selected_branch')
    if not selected_branch: return redirect(url_for('main.branches'))
    declined_transactions = current_app.get_transactions_by_status(get_jwt_identity(), selected_branch, 'Declined')
    return render_template('declined_transactions.html', username=get_jwt_identity(), selected_branch=selected_branch,
                            transactions=declined_transactions, show_sidebar=True, show_notifications_button=True)

@main.route('/add-transaction', methods=['GET', 'POST'])
@jwt_required()
def add_transaction():
    username = get_jwt_identity()
    selected_branch = session.get('selected_branch')
    form = TransactionForm()
    if not selected_branch:
        flash("Please select a branch before adding a transaction.", "error")
        return redirect(url_for('main.branches'))

    if form.validate_on_submit():
        try:
            new_transaction_data = {
                'name_of_issued_check': form.name_of_issued_check.data,
                'check_no': form.check_no.data, 'check_date': form.check_date.data,
                'countered_check': form.countered_check.data, 'check_amount': form.check_amount.data,
                'ewt': form.ewt.data, 'payment_method': form.payment_method.data, 'status': form.status.data
            }
            if current_app.add_transaction(username, selected_branch, new_transaction_data):
                flash('Successfully Added a Transaction!', 'success')
                status_map = {'Paid': 'main.transactions_paid', 'Pending': 'main.transactions_pending', 'Declined': 'main.transactions_declined'}
                return redirect(url_for(status_map.get(form.status.data, 'main.dashboard')))
            else:
                flash('An error occurred while adding the transaction.', 'error')
        except Exception as e:
            logger.error(f"Exception in add_transaction route for user {username}: {e}", exc_info=True)
            flash('An unexpected application error occurred.', 'error')

    return render_template('add_transaction.html', username=username, selected_branch=selected_branch,
                            show_sidebar=True, show_notifications_button=True, form=form)

# Other main routes
@main.route('/archive')
@jwt_required()
def archive():
    return render_template('_archive.html', username=get_jwt_identity(), selected_branch=session.get('selected_branch'),
                           archived_items=archived_items_data, show_sidebar=True, show_notifications_button=True)
@main.route('/billings')
@jwt_required()
def wallet():
    return render_template('billings.html', username=get_jwt_identity(), selected_branch=session.get('selected_branch'),
                           show_sidebar=True, show_notifications_button=True)
@main.route('/analytics')
@jwt_required()
def analytics():
    return render_template('analytics.html', username=get_jwt_identity(), selected_branch=session.get('selected_branch'),
                           revenue_data=analytics_revenue_data, suppliers=analytics_supplier_data,
                           show_sidebar=True, show_notifications_button=True)
@main.route('/invoice')
@jwt_required()
def invoice():
    return render_template('invoice.html', username=get_jwt_identity(), selected_branch=session.get('selected_branch'),
                           show_sidebar=True, show_notifications_button=True)
@main.route('/schedules', methods=['GET'])
@jwt_required()
def schedules():
    return render_template('schedules.html', username=get_jwt_identity(), selected_branch=session.get('selected_branch'),
                           show_sidebar=True, show_notifications_button=True)
@main.route('/settings')
@jwt_required()
def settings():
    return render_template('settings.html', username=get_jwt_identity(), selected_branch=session.get('selected_branch'),
                           show_sidebar=True, show_notifications_button=True)

# --- API and PWA Routes ---
@main.route('/api/schedules', methods=['GET'])
@jwt_required()
def get_schedules():
    username, start_str, end_str = get_jwt_identity(), request.args.get('start'), request.args.get('end')
    if not start_str or not end_str: return jsonify({"error": "Missing start or end parameters"}), 400
    try:
        start_date = datetime.fromisoformat(start_str.replace('Z', '+00:00'))
        end_date = datetime.fromisoformat(end_str.replace('Z', '+00:00'))
    except ValueError:
        return jsonify({"error": "Invalid date format"}), 400
    
    schedules_from_db = current_app.get_schedules_by_date_range(username, start_date, end_date)
    calendar_events = [{
        "id": str(s['_id']), "title": s['title'], "start": s['start_time'], "end": s['end_time'],
        "extendedProps": {"category": s.get('category', 'Others'), "notes": s.get('notes', '')},
        "backgroundColor": get_category_color(s.get('category')), "borderColor": get_category_color(s.get('category'))
    } for s in schedules_from_db]
    return jsonify(calendar_events)

@main.route('/api/invoice/upload', methods=['POST'])
@jwt_required()
def upload_invoice():
    username, selected_branch = get_jwt_identity(), session.get('selected_branch')
    if not selected_branch: return jsonify({'error': 'No branch selected.'}), 400
    if 'invoice_file' not in request.files or not request.files['invoice_file'].filename:
        return jsonify({'error': 'No file selected.'}), 400
    
    file = request.files['invoice_file']
    try:
        original_filename = secure_filename(file.filename)
        file_ext = os.path.splitext(original_filename)[1]
        unique_filename = f"{username}_{datetime.now(pytz.utc).strftime('%Y%m%d%H%M%S%f')}{file_ext}"
        filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], unique_filename)
        file.save(filepath)
        
        invoice_date_str = request.form.get('invoice_date')
        invoice_date = datetime.strptime(invoice_date_str, '%Y-%m-%d') if invoice_date_str else None

        invoice_data = {
            'folder_name': request.form.get('folder_name'), 'category': request.form.get('category'),
            'invoice_date': invoice_date, 'original_filename': original_filename,
            'saved_filename': unique_filename, 'filepath': filepath, 'filesize': os.path.getsize(filepath)
        }
        
        # --- THIS IS THE FIX ---
        # Call the model function via current_app for consistency
        if current_app.add_invoice(username, selected_branch, invoice_data):
            return jsonify({'success': True, 'message': 'File uploaded successfully.'}), 201
        else:
            os.remove(filepath)
            return jsonify({'error': 'Failed to record invoice in database.'}), 500
    except Exception as e:
        logger.error(f"Invoice upload failed for user {username}: {e}", exc_info=True)
        if 'filepath' in locals() and os.path.exists(filepath): os.remove(filepath)
        return jsonify({'error': 'An internal server error occurred.'}), 500

@main.route('/api/transaction/<transaction_id>', methods=['GET'])
@jwt_required()
def get_transaction_details(transaction_id):
    transaction = current_app.get_transaction_by_id(get_jwt_identity(), transaction_id)
    return jsonify(transaction) if transaction else (jsonify({'error': 'Transaction not found.'}), 404)

@main.route('/api/transactions/<transaction_id>', methods=['DELETE'])
@jwt_required()
def delete_transaction_route(transaction_id):
    if current_app.delete_transaction(get_jwt_identity(), transaction_id):
        return jsonify({'success': True, 'message': 'Transaction deleted.'}), 200
    return jsonify({'error': 'Failed to delete transaction.'}), 404

@main.route('/offline')
def offline():
    return render_template('offline.html')

# --- PWA & Notification API Endpoints ---
@main.route('/api/notifications', methods=['GET'])
@jwt_required()
def get_notifications():
    notifications = current_app.get_unread_notifications(get_jwt_identity())
    return jsonify(notifications)

@main.route('/api/notifications/mark-read', methods=['POST'])
@jwt_required()
def mark_read():
    if current_app.mark_notifications_as_read(get_jwt_identity()):
        return jsonify({'success': True}), 200
    return jsonify({'error': 'Failed to mark notifications as read'}), 500

@main.route('/api/push/subscribe', methods=['POST'])
@jwt_required()
def push_subscribe():
    subscription_info = request.json
    if not subscription_info: return jsonify({'error': 'No subscription data provided.'}), 400
    if current_app.save_push_subscription(get_jwt_identity(), subscription_info):
        return jsonify({'success': True}), 201
    return jsonify({'error': 'Failed to save subscription.'}), 500