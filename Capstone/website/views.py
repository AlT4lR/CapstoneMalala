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
    get_analytics_data,
    get_recent_activity,
    archive_transaction,
    get_archived_items,
    get_invoices,
    get_invoice_by_id,
    archive_invoice,
    add_loan
)

logger = logging.getLogger(__name__)
main = Blueprint('main', __name__)

# --- Static Service Worker ---
@main.route('/sw.js')
def service_worker():
    return send_from_directory(os.path.join(main.root_path, 'static', 'js'), 'sw.js', mimetype='application/javascript')

# --- Root / Branch Selection ---
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

# --- Dashboard ---
@main.route('/dashboard')
@jwt_required()
def dashboard():
    selected_branch = session.get('selected_branch')
    if not selected_branch:
        return redirect(url_for('main.branches'))
    username = get_jwt_identity()
    pending_transactions = get_transactions_by_status(username, selected_branch, 'Pending')
    pending_count = len(pending_transactions)
    paid_transactions = get_transactions_by_status(username, selected_branch, 'Paid')
    paid_count = len(paid_transactions)
    recent_activities = get_recent_activity(username, limit=3)
    return render_template(
        'dashboard.html',
        username=username,
        selected_branch=selected_branch,
        show_sidebar=True,
        pending_count=pending_count,
        paid_count=paid_count,
        recent_activities=recent_activities
    )

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
    if not selected_branch:
        return redirect(url_for('main.branches'))
    transactions = get_transactions_by_status(username, selected_branch, 'Pending')
    form = TransactionForm()
    return render_template(
        'pending_transactions.html',
        transactions=transactions,
        selected_branch=selected_branch,
        form=form,
        show_sidebar=True
    )

@main.route('/transactions/paid')
@jwt_required()
def transactions_paid():
    username = get_jwt_identity()
    selected_branch = session.get('selected_branch')
    if not selected_branch:
        return redirect(url_for('main.branches'))
    transactions = get_transactions_by_status(username, selected_branch, 'Paid')
    form = TransactionForm()
    return render_template(
        'paid_transactions.html',
        transactions=transactions,
        form=form,
        show_sidebar=True
    )

@main.route('/add-transaction', methods=['POST'])
@jwt_required()
def add_transaction():
    username = get_jwt_identity()
    selected_branch = session.get('selected_branch')
    form = TransactionForm()
    redirect_url = url_for('main.transactions_pending')
    if request.referrer and 'paid' in request.referrer:
        redirect_url = url_for('main.transactions_paid')
    if form.validate_on_submit():
        if current_app.add_transaction(username, selected_branch, form.data):
            flash('Successfully added a new transaction!', 'success')
            current_app.log_user_activity(username, 'Added a new transaction')
        else:
            flash('An error occurred.', 'error')
    else:
        for field, errors in form.errors.items():
            flash(f"Error in {getattr(form, field).label.text}: {errors[0]}", "error")
    return redirect(redirect_url)

# --- Analytics / Invoice / Others ---
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

@main.route('/api/invoices/upload', methods=['POST'])
@jwt_required()
def upload_invoice():
    username = get_jwt_identity()
    current_app.log_user_activity(username, 'Uploaded an invoice')
    flash('Successfully added an invoice!', 'success')
    return jsonify({'success': True, 'redirect_url': url_for('main.all_invoices')})

@main.route('/billings')
@jwt_required()
def billings():
    # Pass an instance of LoanForm to the template
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

# --- API Routes ---
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
    return jsonify({'error': 'Failed to archive transaction.'}), 404

@main.route('/api/transactions/details/<transaction_id>', methods=['GET'])
@jwt_required()
def get_transaction_details(transaction_id):
    username = get_jwt_identity()
    transaction_data = current_app.get_transaction_by_id(username, transaction_id)
    if transaction_data:
        return jsonify(transaction_data)
    return jsonify({'error': 'Transaction not found'}), 404

@main.route('/api/transactions/<transaction_id>/pay', methods=['POST'])
@jwt_required()
def pay_transaction(transaction_id):
    username = get_jwt_identity()
    data = request.get_json()
    notes = data.get('notes')
    if current_app.mark_transaction_as_paid(username, transaction_id, notes):
        current_app.log_user_activity(username, f'Marked transaction as Paid')
        return jsonify({'success': True, 'message': 'Transaction marked as Paid.'})
    return jsonify({'error': 'Failed to mark transaction as Paid.'}), 400

@main.route('/api/invoices/<invoice_id>', methods=['DELETE'])
@jwt_required()
def delete_invoice_route(invoice_id):
    username = get_jwt_identity()
    if current_app.archive_invoice(username, invoice_id):
        current_app.log_user_activity(username, 'Archived an invoice')
        return jsonify({'success': True}), 200
    return jsonify({'error': 'Failed to archive invoice.'}), 404

@main.route('/api/invoices/details/<invoice_id>', methods=['GET'])
@jwt_required()
def get_invoice_details(invoice_id):
    username = get_jwt_identity()
    invoice_data = current_app.get_invoice_by_id(username, invoice_id)
    if invoice_data:
        return jsonify(invoice_data)
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
        return "Invoice or files not found", 404
    buffer = io.BytesIO()
    p = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter
    image_file_info = invoice['files'][0]
    image_path = os.path.join(current_app.config['UPLOAD_FOLDER'], image_file_info['filename'])
    if not os.path.exists(image_path):
        return "Image file not found on server", 404
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
    """API endpoint to handle adding a new loan."""
    username = get_jwt_identity()
    selected_branch = session.get('selected_branch')
    form = LoanForm()
    if form.validate_on_submit():
        if current_app.add_loan(username, selected_branch, form.data):
            current_app.log_user_activity(username, 'Added a new loan')
            return jsonify({'success': True, 'message': 'Successfully loan added!'})
        else:
            return jsonify({'success': False, 'error': 'An error occurred while saving the loan.'}), 500
    errors = {field: error[0] for field, error in form.errors.items()}
    return jsonify({'success': False, 'errors': errors}), 400

# --- Archive ---
@main.route('/archive')
@jwt_required()
def archive():
    username = get_jwt_identity()
    archived_items = get_archived_items(username)
    return render_template('_archive.html', show_sidebar=True, archived_items=archived_items)