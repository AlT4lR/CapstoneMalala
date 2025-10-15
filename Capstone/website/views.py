# website/views.py

from flask import (
    Blueprint, render_template, request, redirect, url_for, session, flash,
    make_response, current_app, send_from_directory, jsonify, send_file
)
from flask_jwt_extended import jwt_required, get_jwt_identity, verify_jwt_in_request
from datetime import datetime
import os
import logging
import pytesseract
from PIL import Image
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.utils import ImageReader
import io

from .forms import TransactionForm, LoanForm
from .models import (
    get_transactions_by_status,
    get_transaction_by_id,
    get_child_transactions_by_parent_id, # This import is now correct
    get_analytics_data,
    get_recent_activity,
    archive_transaction,
    get_archived_items,
    get_invoices,
    get_invoice_by_id,
    archive_invoice,
    add_loan,
    add_schedule, 
    get_schedules,
    mark_folder_as_paid # This import is now correct
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
def branches(): return render_template('branches.html')

@main.route('/offline')
def offline(): return render_template('offline.html')

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
    if not selected_branch: return redirect(url_for('main.branches'))
    username = get_jwt_identity()
    
    # --- START OF MODIFICATION ---
    # Calculate pending count based on child checks, not folders
    pending_transaction_folders = get_transactions_by_status(username, selected_branch, 'Pending')
    total_pending_checks = 0
    for folder in pending_transaction_folders:
        child_checks = get_child_transactions_by_parent_id(username, folder['_id'])
        total_pending_checks += len(child_checks)
    # --- END OF MODIFICATION ---

    paid_transactions = get_transactions_by_status(username, selected_branch, 'Paid')
    recent_activities = get_recent_activity(username, limit=3)
    
    return render_template(
        'dashboard.html', 
        username=username, 
        selected_branch=selected_branch, 
        show_sidebar=True, 
        pending_count=total_pending_checks, # Use the new count
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
    if not selected_branch: return redirect(url_for('main.branches'))
    transactions = get_transactions_by_status(username, selected_branch, 'Pending')
    return render_template('pending_transactions.html', transactions=transactions, show_sidebar=True)

@main.route('/transactions/paid')
@jwt_required()
def transactions_paid():
    username = get_jwt_identity()
    selected_branch = session.get('selected_branch')
    transactions = get_transactions_by_status(username, selected_branch, 'Paid')
    return render_template('paid_transactions.html', transactions=transactions, show_sidebar=True)

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
    
    return render_template(
        'transaction_folder_detail.html',
        folder=folder,
        child_checks=child_checks,
        form=form,
        show_sidebar=True
    )

@main.route('/add-transaction', methods=['POST'])
@jwt_required()
def add_transaction():
    username = get_jwt_identity()
    selected_branch = session.get('selected_branch')
    form = TransactionForm()
    
    parent_id = request.form.get('parent_id') if request.form.get('parent_id') else None
    
    redirect_url = url_for('main.transaction_folder_details', transaction_id=parent_id) if parent_id else url_for('main.transactions_pending')

    if form.validate_on_submit():
        if current_app.add_transaction(username, selected_branch, form.data, parent_id=parent_id):
            activity = 'Added a new check' if parent_id else 'Created a new transaction folder'
            current_app.log_user_activity(username, activity)
            flash(f'Successfully {activity}!', 'success')
        else:
            flash('An error occurred while saving.', 'error')
    else:
        first_error = next(iter(form.errors.values()))[0]
        flash(f"Error: {first_error}", 'error')

    return redirect(redirect_url)

@main.route('/analytics')
@jwt_required()
def analytics():
    analytics_data = get_analytics_data(get_jwt_identity(), datetime.now().year)
    return render_template('analytics.html', analytics_data=analytics_data, show_sidebar=True)

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
    form = LoanForm()
    return render_template('billings.html', show_sidebar=True, form=form)

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
    return render_template('_archive.html', show_sidebar=True, archived_items=archived_items)

# --- API Routes ---

@main.route('/api/invoices/upload', methods=['POST'])
@jwt_required()
def upload_invoice():
    username = get_jwt_identity()
    current_app.log_user_activity(username, 'Uploaded an invoice')
    flash('Successfully added an invoice!', 'success')
    return jsonify({'success': True, 'redirect_url': url_for('main.all_invoices')})

@main.route('/api/notifications/status', methods=['GET'])
@jwt_required()
def notification_status():
    username = get_jwt_identity()
    count = current_app.get_unread_notification_count(username)
    return jsonify({'unread_count': count})

@main.route('/api/notifications', methods=['GET'])
@jwt_required()
def get_notifications():
    username = get_jwt_identity()
    notifications = current_app.get_unread_notifications(username)
    return jsonify(notifications)

@main.route('/api/notifications/read', methods=['POST'])
@jwt_required()
def mark_read():
    username = get_jwt_identity()
    if current_app.mark_notifications_as_read(username):
        return jsonify({'success': True})
    return jsonify({'error': 'Failed to mark notifications as read'}), 500

@main.route('/api/transactions/<transaction_id>', methods=['DELETE'])
@jwt_required()
def delete_transaction_route(transaction_id):
    username = get_jwt_identity()
    if archive_transaction(username, transaction_id):
        flash('Transaction successfully moved to archive!', 'success')
        current_app.log_user_activity(username, 'Archived a transaction')
        return jsonify({'success': True}), 200
    flash('Failed to archive transaction.', 'error')
    return jsonify({'error': 'Failed to archive transaction.'}), 404

@main.route('/api/transactions/details/<transaction_id>', methods=['GET'])
@jwt_required()
def get_transaction_details(transaction_id):
    username = get_jwt_identity()
    transaction_data = current_app.get_transaction_by_id(username, transaction_id)
    if transaction_data:
        return jsonify(transaction_data)
    flash('Could not find the requested transaction.', 'error')
    return jsonify({'error': 'Transaction not found'}), 404

@main.route('/api/transactions/folder/<folder_id>/pay', methods=['POST'])
@jwt_required()
def pay_transaction_folder(folder_id):
    username = get_jwt_identity()
    data = request.get_json()
    notes = data.get('notes')

    if mark_folder_as_paid(username, folder_id, notes):
        current_app.log_user_activity(username, f'Marked transaction folder as Paid')
        flash('Transaction successfully marked as paid!', 'success')
        return jsonify({'success': True})
    
    flash('Failed to mark transaction as paid.', 'error')
    return jsonify({'error': 'Failed to process payment.'}), 400

@main.route('/api/invoices/<invoice_id>', methods=['DELETE'])
@jwt_required()
def delete_invoice_route(invoice_id):
    username = get_jwt_identity()
    if current_app.archive_invoice(username, invoice_id):
        flash('Invoice successfully moved to archive!', 'success')
        current_app.log_user_activity(username, 'Archived an invoice')
        return jsonify({'success': True}), 200
    flash('Failed to archive invoice.', 'error')
    return jsonify({'error': 'Failed to archive invoice.'}), 404

@main.route('/api/invoices/details/<invoice_id>', methods=['GET'])
@jwt_required()
def get_invoice_details(invoice_id):
    username = get_jwt_identity()
    invoice_data = current_app.get_invoice_by_id(username, invoice_id)
    if invoice_data:
        return jsonify(invoice_data)
    flash('Could not load invoice details.', 'error')
    return jsonify({'error': 'Invoice not found'}), 404

def perform_ocr_on_image(image_path):
    try:
        text = pytesseract.image_to_string(Image.open(image_path))
        return text
    except Exception as e:
        logger.error(f"OCR failed for image {image_path}: {e}")
        return "OCR failed: Could not read text from image."

@main.route('/api/invoices/<invoice_id>/download', methods=['GET'])
@jwt_required()
def download_invoice_as_pdf(invoice_id):
    username = get_jwt_identity()
    invoice = current_app.get_invoice_by_id(username, invoice_id)
    if not invoice or not invoice.get('files'):
        flash('Invoice or files not found.', 'error')
        return redirect(url_for('main.all_invoices'))
    
    buffer = io.BytesIO()
    p = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter
    image_file_info = invoice['files'][0]
    image_path = os.path.join(current_app.config['UPLOAD_FOLDER'], image_file_info['filename'])
    if not os.path.exists(image_path):
        flash('Image file for invoice not found on server.', 'error')
        return redirect(url_for('main.all_invoices'))
        
    extracted_text = perform_ocr_on_image(image_path)
    p.drawString(30, height - 50, f"Invoice: {invoice.get('folder_name', 'N/A')}")
    img_reader = ImageReader(image_path)
    img_width, img_height = img_reader.getSize()
    aspect = img_height / float(img_width)
    display_width = width - 100
    display_height = display_width * aspect
    p.drawImage(img_reader, 50, height - 100 - display_height, width=display_width, height=display_height)
    p.showPage()
    p.drawString(30, height - 50, "Extracted Text (OCR)")
    text_object = p.beginText(40, height - 80)
    text_object.setFont("Helvetica", 10)
    for line in extracted_text.splitlines():
        text_object.textLine(line)
    p.drawText(text_object)
    p.save()
    buffer.seek(0)
    return send_file(
        buffer, as_attachment=True,
        download_name=f"{invoice.get('folder_name', 'invoice')}.pdf",
        mimetype='application/pdf'
    )

@main.route('/api/loans/add', methods=['POST'])
@jwt_required()
def add_loan_route():
    username = get_jwt_identity()
    selected_branch = session.get('selected_branch')
    form = LoanForm()
    if form.validate_on_submit():
        if current_app.add_loan(username, selected_branch, form.data):
            current_app.log_user_activity(username, 'Added a new loan')
            flash('Successfully added a new loan!', 'success')
            return jsonify({'success': True})
    
    flash('Failed to add the new loan. Please check the details.', 'error')
    errors = {field: error[0] for field, error in form.errors.items()}
    return jsonify({'success': False, 'errors': errors}), 400

@main.route('/api/schedules', methods=['GET'])
@jwt_required()
def get_schedules_route():
    username = get_jwt_identity()
    start = request.args.get('start')
    end = request.args.get('end')
    if not start or not end:
        return jsonify({"error": "Start and end date are required"}), 400
    events = current_app.get_schedules(username, start, end)
    return jsonify(events)

@main.route('/api/schedules/add', methods=['POST'])
@jwt_required()
def add_schedule_route():
    username = get_jwt_identity()
    if not request.form:
        return jsonify({"error": "Form data is missing"}), 400
    if current_app.add_schedule(username, request.form):
        current_app.log_user_activity(username, "Created a new schedule")
        flash('Schedule created successfully!', 'success')
        return jsonify({"success": True})
    
    flash('Failed to create schedule.', 'error')
    return jsonify({"error": "Failed to create schedule"}), 500
