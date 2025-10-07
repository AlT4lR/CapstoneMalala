from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify, make_response, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity, verify_jwt_in_request
from datetime import datetime
import pytz
import os
from werkzeug.utils import secure_filename

from .forms import TransactionForm
from . import zoho_api
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
        'Office': '#93c5fd', 'Meetings': '#fca5a5', 'Events': '#f9a8d4',
        'Personal': '#6ee7b7', 'Others': '#a5b4fc'
    }
    return colors.get(category, '#a5b4fc')

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

# --- Transaction Routes (Merged V2 logic with V3 approach) ---

# The transaction list pages now only serve the template, expecting JS to fetch data via API.
@main.route('/transactions/paid')
@jwt_required()
def transactions_paid():
    selected_branch = session.get('selected_branch')
    if not selected_branch: return redirect(url_for('main.branches'))
    return render_template('paid_transactions.html', username=get_jwt_identity(), selected_branch=selected_branch, show_sidebar=True, show_notifications_button=True)

@main.route('/transactions/pending')
@jwt_required()
def transactions_pending():
    selected_branch = session.get('selected_branch')
    if not selected_branch: return redirect(url_for('main.branches'))
    return render_template('pending_transactions.html', username=get_jwt_identity(), selected_branch=selected_branch, show_sidebar=True, show_notifications_button=True)

@main.route('/transactions/declined')
@jwt_required()
def transactions_declined():
    selected_branch = session.get('selected_branch')
    if not selected_branch: return redirect(url_for('main.branches'))
    return render_template('declined_transactions.html', username=get_jwt_identity(), selected_branch=selected_branch, show_sidebar=True, show_notifications_button=True)

# The add_transaction route now only serves the form page (GET)
@main.route('/add-transaction', methods=['GET'])
@jwt_required()
def add_transaction_page():
    username = get_jwt_identity()
    selected_branch = session.get('selected_branch')
    form = TransactionForm()
    if not selected_branch:
        flash("Please select a branch before adding a transaction.", "error")
        return redirect(url_for('main.branches'))
    return render_template('add_transaction.html', username=username, selected_branch=selected_branch,
                            show_sidebar=True, show_notifications_button=True, form=form)

# The old mixed GET/POST add_transaction route is REMOVED/REPLACED by the above and the API route below.

# --- API Routes for Transactions (New/Updated) ---

@main.route('/api/transactions/add', methods=['POST'])
@jwt_required()
def add_transaction_api():
    username = get_jwt_identity()
    selected_branch = session.get('selected_branch')
    if not selected_branch:
        return jsonify({'error': 'No branch selected.'}), 400

    data = request.get_json()
    # Convert date string from form/outbox to datetime object
    data['check_date'] = datetime.strptime(data['check_date'], '%Y-%m-%d').date()

    if current_app.add_transaction(username, selected_branch, data):
        return jsonify({'success': True, 'message': 'Transaction added successfully.'}), 201
    else:
        return jsonify({'error': 'An error occurred while adding the transaction.'}), 500

@main.route('/api/transactions/paid', methods=['GET'])
@jwt_required()
def get_paid_transactions_api():
    transactions = current_app.get_transactions_by_status(get_jwt_identity(), session.get('selected_branch'), 'Paid')
    return jsonify(transactions)

@main.route('/api/transactions/pending', methods=['GET'])
@jwt_required()
def get_pending_transactions_api():
    transactions = current_app.get_transactions_by_status(get_jwt_identity(), session.get('selected_branch'), 'Pending')
    return jsonify(transactions)

@main.route('/api/transactions/declined', methods=['GET'])
@jwt_required()
def get_declined_transactions_api():
    transactions = current_app.get_transactions_by_status(get_jwt_identity(), session.get('selected_branch'), 'Declined')
    return jsonify(transactions)

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


# --- Other main routes (Unchanged) ---
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
@main.route('/invoices')
@jwt_required()
def invoice_list():
    username = get_jwt_identity()
    selected_branch = session.get('selected_branch')
    if not selected_branch:
        flash("Please select a branch to view invoices.", "info")
        return redirect(url_for('main.branches'))
    
    invoices = current_app.get_invoices(username, selected_branch)
    return render_template('invoice_list.html', 
                            username=username, 
                            selected_branch=selected_branch,
                            invoices=invoices,
                            show_sidebar=True, 
                            show_notifications_button=True)

@main.route('/invoice/upload')
@jwt_required()
def invoice():
    return render_template('invoice.html', username=get_jwt_identity(), selected_branch=session.get('selected_branch'),
                            show_sidebar=True, show_notifications_button=True)
                            
@main.route('/schedules', methods=['GET'])
@jwt_required()
def schedules():
    username = get_jwt_identity()
    # Fetch categories for the current user to populate the sidebar and modal
    categories = current_app.get_all_categories(username)
    return render_template('schedules.html', 
                            username=username, 
                            selected_branch=session.get('selected_branch'),
                            categories=categories,
                            get_category_color=get_category_color,
                            show_sidebar=True, 
                            show_notifications_button=True)

@main.route('/settings')
@jwt_required()
def settings():
    return render_template('settings.html', username=get_jwt_identity(), selected_branch=session.get('selected_branch'),
                            show_sidebar=True, show_notifications_button=True)

# Zoho OAuth Routes
@main.route('/zoho/connect')
@jwt_required()
def zoho_connect():
    auth_url = zoho_api.get_auth_url()
    return redirect(auth_url)

@main.route('/zoho/callback')
@jwt_required()
def zoho_callback():
    username = get_jwt_identity()
    code = request.args.get('code')
    if not code:
        flash('Zoho connection failed: No authorization code provided.', 'error')
        return redirect(url_for('main.settings'))

    token_data = zoho_api.exchange_code_for_tokens(code)
    if not token_data:
        flash('Failed to get access token from Zoho.', 'error')
        return redirect(url_for('main.settings'))
        
    current_app.save_zoho_tokens(username, token_data)
    
    # After getting tokens, fetch and save the user's primary calendar
    calendars = zoho_api.get_calendars(token_data['access_token'])
    if calendars:
        primary_cal = next((cal for cal in calendars if cal.get('is_primary')), calendars[0])
        current_app.save_primary_calendar(username, primary_cal['calendar_id'])

    flash('Successfully connected your Zoho Calendar!', 'success')
    return redirect(url_for('main.schedules'))


# --- API and PWA Routes ---
# Rewritten to use Zoho API
@main.route('/api/schedules', methods=['GET'])
@jwt_required()
def get_schedules():
    username = get_jwt_identity()
    tokens = current_app.get_zoho_tokens(username)

    if not tokens or not tokens.get('access_token'):
        return jsonify({"error": "Zoho Calendar not connected."}), 401
    
    calendar_id = tokens.get('primary_calendar_id')
    if not calendar_id:
        return jsonify({"error": "Primary Zoho calendar not set."}), 400
        
    start_str, end_str = request.args.get('start'), request.args.get('end')
    try:
        start_date = datetime.fromisoformat(start_str.replace('Z', '+00:00'))
        end_date = datetime.fromisoformat(end_str.replace('Z', '+00:00'))
    except (ValueError, TypeError):
        return jsonify({"error": "Invalid date format"}), 400
    
    zoho_events = zoho_api.get_events(tokens['access_token'], calendar_id, start_date, end_date)
    
    # Transform Zoho event format to FullCalendar format
    calendar_events = [{
        "id": event['event_id'], 
        "title": event['title'], 
        "start": event['start_time'], 
        "end": event['end_time'],
        "extendedProps": {"notes": event.get('description', '')},
    } for event in zoho_events]
    
    return jsonify(calendar_events)

@main.route('/api/schedules/create', methods=['POST'])
@jwt_required()
def create_schedule():
    username = get_jwt_identity()
    tokens = current_app.get_zoho_tokens(username)

    if not tokens or not tokens.get('access_token'):
        return jsonify({"error": "Zoho Calendar not connected."}), 401
    
    calendar_id = tokens.get('primary_calendar_id')
    if not calendar_id:
        return jsonify({"error": "Primary Zoho calendar not set."}), 400

    event_data = request.get_json()
    result = zoho_api.create_event(tokens['access_token'], calendar_id, event_data)

    if result:
        return jsonify({'success': True, 'message': 'Event created in Zoho Calendar.'}), 201
    else:
        return jsonify({'error': 'Failed to create event in Zoho Calendar.'}), 500

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
        
        if current_app.add_invoice(username, selected_branch, invoice_data):
            return jsonify({'success': True, 'message': 'File uploaded successfully.'}), 201
        else:
            os.remove(filepath)
            return jsonify({'error': 'Failed to record invoice in database.'}), 500
    except Exception as e:
        logger.error(f"Invoice upload failed for user {username}: {e}", exc_info=True)
        if 'filepath' in locals() and os.path.exists(filepath): os.remove(filepath)
        return jsonify({'error': 'An internal server error occurred.'}), 500

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