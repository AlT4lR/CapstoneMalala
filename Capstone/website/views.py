# website/views.py

from flask import (
    Blueprint, render_template, request, redirect, url_for, session, flash,
    make_response, current_app, send_from_directory, jsonify, send_file, abort
)
from flask_jwt_extended import jwt_required, get_jwt_identity, verify_jwt_in_request
from datetime import datetime, date
import os
import logging
from werkzeug.utils import secure_filename
import pytesseract
from PIL import Image
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.utils import ImageReader
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.platypus import Paragraph
from reportlab.lib.styles import getSampleStyleSheet
import io

from .forms import TransactionForm, LoanForm, EditTransactionForm
from .models import (
    get_user_by_username, get_user_by_email, add_user, check_password, update_last_login,
    record_failed_login_attempt, set_user_otp, verify_user_otp, update_user_password,
    add_transaction, get_transactions_by_status, get_transaction_by_id, update_transaction,
    archive_transaction, get_archived_items, get_child_transactions_by_parent_id,
    mark_folder_as_paid,
    get_analytics_data,
    log_user_activity, get_recent_activity,
    add_invoice, get_invoices, get_invoice_by_id, archive_invoice,
    add_notification, get_unread_notifications, get_unread_notification_count, mark_notifications_as_read, save_push_subscription, get_user_push_subscriptions,
    add_loan, get_loans,
    add_schedule, get_schedules, update_schedule, delete_schedule,
    restore_item, delete_item_permanently,
    get_weekly_billing_summary
)


logger = logging.getLogger(__name__)
main = Blueprint('main', __name__)

# --- Static Service Worker ---
@main.route('/sw.js')
def service_worker():
    return send_from_directory(os.path.join(main.root_path, 'static', 'js'), 'sw.js', mimetype='application/javascript')

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

@main.route('/offline')
def offline():
    return render_template('offline.html')

@main.route('/select_branch/<branch_name>')
@jwt_required()
def select_branch(branch_name):
    if branch_name.upper() in ['MONTALBAN', 'LAGUNA']:
        session['selected_branch'] = branch_name.upper()
    return redirect(url_for('main.dashboard'))

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
    return render_template(
        'dashboard.html',
        username=username,
        selected_branch=selected_branch,
        show_sidebar=True,
        pending_count=len(pending_transactions),
        paid_count=len(paid_transactions),
        recent_activities=recent_activities
    )

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
    if not selected_branch:
        return redirect(url_for('main.branches'))
    transactions = get_transactions_by_status(username, selected_branch, 'Pending')
    return render_template('pending_transactions.html', transactions=transactions, show_sidebar=True)

@main.route('/transactions/paid')
@jwt_required()
def transactions_paid():
    username = get_jwt_identity()
    selected_branch = session.get('selected_branch')
    transactions = get_transactions_by_status(username, selected_branch, 'Paid')
    edit_form = EditTransactionForm()
    return render_template('paid_transactions.html', transactions=transactions, show_sidebar=True, edit_form=edit_form)

@main.route('/transaction/folder/<transaction_id>')
@jwt_required()
def transaction_folder_details(transaction_id):
    username = get_jwt_identity()
    folder = get_transaction_by_id(username, transaction_id, full_document=True)
    if not folder:
        flash('Transaction folder not found.', 'error')
        return redirect(url_for('main.transactions_pending'))
    
    child_checks = get_child_transactions_by_parent_id(username, transaction_id)
    form = TransactionForm()
    total_countered_check = sum(check.get('countered_check', 0) for check in child_checks)
    
    return render_template(
        'transaction_folder_detail.html',
        folder=folder,
        child_checks=child_checks,
        form=form,
        total_countered_check=total_countered_check,
        show_sidebar=True
    )

@main.route('/add-transaction', methods=['POST'])
@jwt_required()
def add_transaction_route():
    username = get_jwt_identity()
    selected_branch = session.get('selected_branch')
    form = TransactionForm()
    parent_id = request.form.get('parent_id') if request.form.get('parent_id') else None
    
    if form.validate_on_submit():
        if not parent_id: # This is a new folder
            if add_transaction(username, selected_branch, form.data):
                log_user_activity(username, 'Created a new transaction folder')
                flash('Successfully created a new transaction folder!', 'success')
                return jsonify({'success': True, 'redirect_url': url_for('main.transactions_pending')})
            else:
                flash('An error occurred while saving the folder.', 'error')
                return jsonify({'success': False, 'error': 'Database error'}), 500
        else: # This is a child check being added to a folder
            if add_transaction(username, selected_branch, form.data, parent_id=parent_id):
                log_user_activity(username, 'Added a new check to a folder')
                flash('Successfully added a new check!', 'success')
            else:
                flash('An error occurred while saving the check.', 'error')
            return redirect(url_for('main.transaction_folder_details', transaction_id=parent_id))
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({'success': False, 'errors': form.errors}), 400
    
    for field, errors in form.errors.items():
        for error in errors:
            flash(error, 'error')
    
    redirect_url = url_for('main.transaction_folder_details', transaction_id=parent_id) if parent_id else url_for('main.transactions')
    return redirect(redirect_url)


# --- START OF MODIFICATION ---
@main.route('/analytics')
@jwt_required()
def analytics():
    username = get_jwt_identity()
    selected_branch = session.get('selected_branch')
    if not selected_branch:
        flash('Please select a branch first.', 'error')
        return redirect(url_for('main.branches'))
    
    initial_data = get_analytics_data(username, selected_branch, datetime.now().year, datetime.now().month)
    return render_template('analytics.html', analytics_data=initial_data, show_sidebar=True)
# --- END OF MODIFICATION ---

@main.route('/invoice')
@jwt_required()
def invoice():
    return render_template('invoice.html', show_sidebar=True)

@main.route('/invoices')
@jwt_required()
def all_invoices():
    username = get_jwt_identity()
    selected_branch = session.get('selected_branch')
    invoice_list = get_invoices(username, selected_branch)
    return render_template('all_invoices.html', show_sidebar=True, invoices=invoice_list)

@main.route('/billings')
@jwt_required()
def billings():
    username = get_jwt_identity()
    selected_branch = session.get('selected_branch')
    form = LoanForm()
    loans = get_loans(username, selected_branch)
    return render_template('billings.html', show_sidebar=True, form=form, loans=loans)

@main.route('/schedules')
@jwt_required()
def schedules():
    return render_template('schedules.html', show_sidebar=True)

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

# --- API Routes ---
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

# --- START OF MODIFICATION ---
@main.route('/api/analytics/summary', methods=['GET'])
@jwt_required()
def get_analytics_summary():
    username = get_jwt_identity()
    selected_branch = session.get('selected_branch')
    if not selected_branch:
        return jsonify({'error': 'Branch not selected'}), 400
        
    try:
        year = int(request.args.get('year', datetime.now().year))
        month = int(request.args.get('month', datetime.now().month))
        if not (1 <= month <= 12):
            raise ValueError("Month is out of range")
    except (TypeError, ValueError):
        return jsonify({'error': 'Invalid year or month parameter'}), 400

    summary_data = get_analytics_data(username, selected_branch, year, month)
    return jsonify(summary_data)
# --- END OF MODIFICATION ---

@main.route('/api/billings/summary', methods=['GET'])
@jwt_required()
def get_billings_summary():
    username = get_jwt_identity()
    try:
        year = int(request.args.get('year'))
        week = int(request.args.get('week'))
    except (TypeError, ValueError):
        return jsonify({'error': 'Invalid year or week parameter'}), 400

    summary_data = get_weekly_billing_summary(username, year, week)
    return jsonify(summary_data)

@main.route('/api/invoices/upload', methods=['POST'])
@jwt_required()
def upload_invoice():
    username = get_jwt_identity()
    selected_branch = session.get('selected_branch')
    
    if 'files' not in request.files:
        return jsonify({'success': False, 'error': 'No file part'}), 400
    
    files = request.files.getlist('files')
    if not files or files[0].filename == '':
        return jsonify({'success': False, 'error': 'No selected file'}), 400

    invoice_data = {
        'folder_name': request.form.get('folder-name'),
        'category': request.form.get('categories'),
        'date': datetime.strptime(request.form.get('date'), '%Y-%m-%d') if request.form.get('date') else None,
    }
    
    processed_files_info = []
    extracted_text_all = []

    for file in files:
        if file:
            filename = secure_filename(file.filename)
            filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            extracted_text = perform_ocr_on_image(filepath)
            extracted_text_all.append(extracted_text)
            processed_files_info.append({
                'filename': filename, 'content_type': file.content_type,
                'size': os.path.getsize(filepath)
            })

    if add_invoice(username, selected_branch, invoice_data, processed_files_info, "\n\n".join(extracted_text_all)):
        log_user_activity(username, 'Uploaded an invoice')
        return jsonify({'success': True, 'redirect_url': url_for('main.all_invoices')})
    else:
        return jsonify({'success': False, 'error': 'Database error'}), 500

@main.route('/api/notifications/status', methods=['GET'])
@jwt_required()
def notification_status():
    username = get_jwt_identity()
    count = get_unread_notification_count(username)
    return jsonify({'unread_count': count})

@main.route('/api/notifications', methods=['GET'])
@jwt_required()
def get_notifications():
    username = get_jwt_identity()
    notifications = get_unread_notifications(username)
    return jsonify(notifications)

@main.route('/api/notifications/read', methods=['POST'])
@jwt_required()
def mark_read():
    username = get_jwt_identity()
    if mark_notifications_as_read(username):
        return jsonify({'success': True})
    return jsonify({'error': 'Failed to mark notifications as read'}), 500

@main.route('/api/transactions/<transaction_id>', methods=['DELETE'])
@jwt_required()
def delete_transaction_route(transaction_id):
    username = get_jwt_identity()
    if archive_transaction(username, transaction_id):
        log_user_activity(username, 'Archived a transaction')
        return jsonify({'success': True}), 200
    return jsonify({'error': 'Failed to archive transaction.'}), 404

@main.route('/api/transactions/details/<transaction_id>', methods=['GET'])
@jwt_required()
def get_transaction_details(transaction_id):
    username = get_jwt_identity()
    transaction_data = get_transaction_by_id(username, transaction_id)
    if transaction_data:
        return jsonify(transaction_data)
    return jsonify({'error': 'Transaction not found'}), 404

@main.route('/api/transactions/folder/<folder_id>/pay', methods=['POST'])
@jwt_required()
def pay_transaction_folder(folder_id):
    username = get_jwt_identity()
    data = request.get_json()
    if not data:
        flash('Invalid request data.', 'error')
        return jsonify({'success': False, 'error': 'Invalid request data.'}), 400

    notes, amount = data.get('notes'), data.get('amount')

    if amount is None or not isinstance(amount, (int, float)) or amount <= 0:
        flash('Please enter a valid check amount.', 'error')
        return jsonify({'success': False, 'error': 'A valid amount is required.'}), 400

    if mark_folder_as_paid(username, folder_id, notes, amount):
        log_user_activity(username, f'Marked transaction folder as Paid')
        flash('Transaction successfully marked as Paid!', 'success')
        return jsonify({'success': True})
    else:
        flash('Failed to process payment. Please try again.', 'error')
        return jsonify({'success': False, 'error': 'Failed to process payment.'}), 400

@main.route('/api/invoices/<invoice_id>', methods=['DELETE'])
@jwt_required()
def delete_invoice_route(invoice_id):
    username = get_jwt_identity()
    if archive_invoice(username, invoice_id):
        log_user_activity(username, 'Archived an invoice')
        return jsonify({'success': True}), 200
    return jsonify({'error': 'Failed to archive invoice.'}), 404

@main.route('/api/invoices/details/<invoice_id>', methods=['GET'])
@jwt_required()
def get_invoice_details(invoice_id):
    username = get_jwt_identity()
    invoice_data = get_invoice_by_id(username, invoice_id)
    if invoice_data:
        return jsonify(invoice_data)
    return jsonify({'error': 'Invoice not found'}), 404

def perform_ocr_on_image(image_path):
    try:
        return pytesseract.image_to_string(Image.open(image_path))
    except Exception as e:
        logger.error(f"OCR failed for image {image_path}: {e}")
        return "OCR failed: Could not read text from image."

@main.route('/api/invoices/<invoice_id>/download', methods=['GET'])
@jwt_required()
def download_invoice_as_pdf(invoice_id):
    pass

@main.route('/api/transactions/<transaction_id>/download_pdf', methods=['GET'])
@jwt_required()
def download_transaction_pdf(transaction_id):
    username = get_jwt_identity()
    transaction = get_transaction_by_id(username, transaction_id, full_document=True)
    if not transaction: abort(404)
    buffer = io.BytesIO()
    p = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter
    p.setFont("Helvetica-Bold", 16); p.drawString(inch, height - inch, "Transaction Details")
    p.setFillColor(colors.HexColor("#d1fae5")); p.setStrokeColor(colors.HexColor("#6ee7b7"))
    p.roundRect(inch, height - 1.75*inch, width - 2*inch, 0.5*inch, 10, stroke=1, fill=1)
    p.setFillColor(colors.HexColor("#065f46")); p.setFont("Helvetica-Bold", 12)
    p.drawString(inch * 1.2, height - 1.5*inch, "Paid")
    amount_str = f"₱{transaction.get('amount', 0.0):,.2f}"
    p.setFont("Helvetica-Bold", 14); p.drawRightString(width - inch * 1.2, height - 1.5*inch, amount_str)
    p.setFillColor(colors.black); p.setFont("Helvetica-Bold", 12)
    p.drawString(inch, height - 2.5*inch, "Details")
    p.setFont("Helvetica", 10)
    details = [
        ("Recipient", transaction.get('name', 'N/A')),
        ("Check Date", transaction.get('check_date').strftime('%m/%d/%Y') if transaction.get('check_date') else 'N/A'),
        ("EWT", f"₱{transaction.get('ewt', 0.0):,.2f}"),
        ("Countered Check", f"₱{transaction.get('countered_check', 0.0):,.2f}")
    ]
    y_pos = height - 2.8*inch
    for label, value in details:
        p.setFillColor(colors.gray); p.drawString(inch, y_pos, label)
        p.setFillColor(colors.black); p.drawRightString(width - inch, y_pos, value)
        y_pos -= 0.3*inch
    p.setFont("Helvetica-Bold", 12); p.drawString(inch, y_pos - 0.5*inch, "Notes")
    notes = transaction.get('notes', 'No notes provided.').replace('\n', '<br/>')
    p_style = getSampleStyleSheet()['Normal']
    notes_p = Paragraph(notes, p_style)
    w, h = notes_p.wrapOn(p, width - 2*inch, height)
    notes_p.drawOn(p, inch, y_pos - 0.6*inch - h)
    p.showPage(); p.save()
    buffer.seek(0)
    return send_file(buffer, as_attachment=True, download_name=f"txn_{transaction_id}.pdf", mimetype='application/pdf')

@main.route('/api/transactions/update/<transaction_id>', methods=['POST'])
@jwt_required()
def update_transaction_route(transaction_id):
    username = get_jwt_identity()
    form = EditTransactionForm()
    if form.validate_on_submit():
        if update_transaction(username, transaction_id, form.data):
            log_user_activity(username, f'Updated transaction')
            flash('Transaction updated successfully!', 'success')
            return jsonify({'success': True})
        else:
            return jsonify({'success': False, 'error': 'Database update failed.'}), 500
    return jsonify({'success': False, 'errors': form.errors}), 400

@main.route('/api/loans/add', methods=['POST'])
@jwt_required()
def add_loan_route():
    username = get_jwt_identity()
    selected_branch = session.get('selected_branch')
    form = LoanForm()
    if form.validate_on_submit():
        if add_loan(username, selected_branch, form.data):
            log_user_activity(username, 'Added a new loan')
            flash('Successfully added a new loan!', 'success')
            return jsonify({'success': True})
    return jsonify({'success': False, 'errors': form.errors}), 400

@main.route('/api/schedules', methods=['GET'])
@jwt_required()
def get_schedules_route():
    username = get_jwt_identity()
    start, end = request.args.get('start'), request.args.get('end')
    if not start or not end: return jsonify({"error": "Start and end date are required"}), 400
    return jsonify(get_schedules(username, start, end))

@main.route('/api/schedules/add', methods=['POST'])
@jwt_required()
def add_schedule_route():
    username = get_jwt_identity()
    if not request.form: return jsonify({"error": "Form data is missing"}), 400
    if add_schedule(username, request.form):
        log_user_activity(username, "Created a new schedule")
        return jsonify({"success": True})
    return jsonify({"error": "Failed to create schedule"}), 500

@main.route('/api/schedules/update/<schedule_id>', methods=['POST'])
@jwt_required()
def update_schedule_route(schedule_id):
    username = get_jwt_identity()
    data = request.get_json()
    if not data: return jsonify({'error': 'Invalid data'}), 400
    if update_schedule(username, schedule_id, data):
        log_user_activity(username, "Updated a schedule")
        return jsonify({'success': True})
    return jsonify({'error': 'Update failed'}), 500

@main.route('/api/schedules/<schedule_id>', methods=['DELETE'])
@jwt_required()
def delete_schedule_route(schedule_id):
    username = get_jwt_identity()
    if delete_schedule(username, schedule_id):
        log_user_activity(username, "Deleted a schedule")
        return jsonify({'success': True})
    return jsonify({'error': 'Delete failed'}), 500

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