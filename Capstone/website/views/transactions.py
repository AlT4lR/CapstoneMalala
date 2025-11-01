# website/views/transactions.py

from flask import render_template, request, redirect, url_for, session, flash, jsonify, send_file, abort, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.platypus import Paragraph
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.utils import ImageReader
import io
import os
import logging

from . import main
from ..forms import TransactionForm, EditTransactionForm
from ..models import (
    log_user_activity, add_transaction, get_transactions_by_status, 
    get_transaction_by_id, get_child_transactions_by_parent_id,
    mark_folder_as_paid, archive_transaction, update_transaction
)

logger = logging.getLogger(__name__)

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
    edit_form = EditTransactionForm() 
    return render_template('pending_transactions.html', transactions=transactions, show_sidebar=True, edit_form=edit_form)

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

@main.route('/transaction/paid/folder/<transaction_id>')
@jwt_required()
def paid_transaction_folder_details(transaction_id):
    username = get_jwt_identity()
    folder = get_transaction_by_id(username, transaction_id, full_document=True)

    if not folder or folder.get('status') != 'Paid':
        flash('Paid transaction folder not found.', 'error')
        return redirect(url_for('main.transactions_paid'))
    
    child_checks = get_child_transactions_by_parent_id(username, transaction_id)
    total_countered_check = sum(check.get('countered_check', 0) for check in child_checks)
    
    return render_template(
        'paid_transaction_folder_detail.html',
        folder=folder,
        child_checks=child_checks,
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
        if not parent_id: 
            if add_transaction(username, selected_branch, form.data):
                log_user_activity(username, 'Created a new transaction folder')
                flash('Successfully created a new transaction folder!', 'success')
                return jsonify({'success': True, 'redirect_url': url_for('main.transactions')})
            else:
                flash('An error occurred while saving the folder.', 'error')
                return jsonify({'success': False, 'error': 'Database error'}), 500
        else:
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

# --- Transaction API Routes ---
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

    notes = data.get('notes')

    if mark_folder_as_paid(username, folder_id, notes):
        log_user_activity(username, f'Marked transaction folder as Paid')
        flash('Transaction successfully marked as Paid!', 'success')
        return jsonify({'success': True})
    else:
        flash('Failed to process payment. Please try again.', 'error')
        return jsonify({'success': False, 'error': 'Failed to process payment.'}), 400

@main.route('/api/transactions/<transaction_id>/download_pdf', methods=['GET'])
@jwt_required()
def download_transaction_pdf(transaction_id):
    username = get_jwt_identity()
    folder = get_transaction_by_id(username, transaction_id, full_document=True)
    if not folder or folder.get('status') != 'Paid':
        abort(404)

    child_checks = get_child_transactions_by_parent_id(username, transaction_id)
    total_countered_check = sum(check.get('countered_check', 0) for check in child_checks)

    buffer = io.BytesIO()
    p = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter
    
    p.setFont("Helvetica-Bold", 16)
    p.drawCentredString(width / 2.0, height - 0.75 * inch, "CLEARED ISSUED CHECKS")

    try:
        logo_path = os.path.join(current_app.root_path, 'static', 'imgs', 'icons', 'Cleared_check_logo.png')
        if os.path.exists(logo_path):
            logo_size = 1.2 * inch
            x_position = width - (0.75 * inch) - logo_size
            y_position = height - (0.5 * inch) - logo_size
            p.drawImage(logo_path, x_position, y_position, width=logo_size, height=logo_size, preserveAspectRatio=True, mask='auto')
    except Exception as e:
        logger.error(f"Could not draw logo on PDF: {e}")

    p.setFont("Helvetica", 11)
    p.drawString(0.75 * inch, height - 1.25 * inch, "DECOLORES RETAIL CORPORATION")
    p.drawString(0.75 * inch, height - 1.45 * inch, f"#{str(folder.get('_id'))}")
    
    folder_name = folder.get('name', 'N/A')
    p.drawString(0.75 * inch, height - 1.65 * inch, folder_name)
    name_width = p.stringWidth(folder_name, "Helvetica", 11)
    p.line(0.75 * inch, height - 1.67 * inch, 0.75 * inch + name_width, height - 1.67 * inch)
    
    paid_date = folder.get('paidAt').strftime('%B %d, %Y') if folder.get('paidAt') else 'N/A'
    p.drawString(0.75 * inch, height - 1.85 * inch, paid_date)

    p.line(0.75 * inch, height - 2.1 * inch, width - 0.75 * inch, height - 2.1 * inch)
    
    y_pos = height - 2.5 * inch
    headers = ["Name Issued Check", "Check No.", "Check Date", "EWT", "Countered Check"]
    col_widths = [2.5 * inch, 1.2 * inch, 1.2 * inch, 1.2 * inch, 1.4 * inch]
    x_offset = 0.75 * inch

    p.setFillColor(colors.HexColor("#3a4d39"))
    p.rect(x_offset, y_pos, sum(col_widths), 0.3 * inch, fill=1)
    p.setFillColor(colors.white)
    p.setFont("Helvetica-Bold", 10)
    
    current_x = x_offset
    for i, header in enumerate(headers):
        p.drawCentredString(current_x + col_widths[i] / 2, y_pos + 0.1 * inch, header)
        current_x += col_widths[i]
    
    p.setFont("Helvetica", 9)
    p.setFillColor(colors.black)
    p.setStrokeColor(colors.black)
    y_pos -= (0.25 * inch)
    row_height = 0.25 * inch

    for check in child_checks:
        current_x = x_offset
        p.grid([x_offset, x_offset + col_widths[0], x_offset + sum(col_widths[:2]), x_offset + sum(col_widths[:3]), x_offset + sum(col_widths[:4]), x_offset + sum(col_widths)], [y_pos, y_pos + row_height])
        p.drawString(current_x + 0.1 * inch, y_pos + 0.08 * inch, str(check.get('name', '')))
        current_x += col_widths[0]
        p.drawCentredString(current_x + col_widths[1]/2, y_pos + 0.08 * inch, str(check.get('check_no', '')))
        current_x += col_widths[1]
        date_str = check.get('check_date').strftime('%m/%d/%Y') if check.get('check_date') else ''
        p.drawCentredString(current_x + col_widths[2]/2, y_pos + 0.08 * inch, date_str)
        current_x += col_widths[2]
        p.drawRightString(current_x + col_widths[3] - 0.1 * inch, y_pos + 0.08 * inch, f"{check.get('ewt', 0):,.2f}")
        current_x += col_widths[3]
        p.drawRightString(current_x + col_widths[4] - 0.1 * inch, y_pos + 0.08 * inch, f"{check.get('countered_check', 0):,.2f}")
        y_pos -= row_height

    for _ in range(len(child_checks), 12):
        p.grid([x_offset, x_offset + col_widths[0], x_offset + sum(col_widths[:2]), x_offset + sum(col_widths[:3]), x_offset + sum(col_widths[:4]), x_offset + sum(col_widths)], [y_pos, y_pos + row_height])
        y_pos -= row_height

    # --- START OF FIX: Adjust label position to prevent collision ---
    p.setFont("Helvetica", 10)
    summary_box_x = width - 2.75 * inch
    summary_label_end_x = summary_box_x - 0.1 * inch # Position label to the left of the box
    summary_y = y_pos - 0.3 * inch
    
    p.drawRightString(summary_label_end_x, summary_y + 0.35 * inch, "Countered Checks")
    p.rect(summary_box_x, summary_y + 0.25 * inch, 2.0 * inch, 0.25 * inch)
    p.drawRightString(summary_box_x + 1.95 * inch, summary_y + 0.35 * inch, f"₱ {total_countered_check:,.2f}")
    
    p.setFont("Helvetica-Bold", 10)
    p.drawRightString(summary_label_end_x, summary_y + 0.1 * inch, "Check Amount")
    p.rect(summary_box_x, summary_y, 2.0 * inch, 0.25 * inch)
    p.drawRightString(summary_box_x + 1.95 * inch, summary_y + 0.1 * inch, f"₱ {folder.get('amount', 0.0):,.2f}")
    # --- END OF FIX ---

    p.setFont("Helvetica-Bold", 11)
    notes_y_start = y_pos - 1.2 * inch
    p.drawString(x_offset, notes_y_start, "Notes")
    p.rect(x_offset, 1 * inch, width - 1.5 * inch, notes_y_start - 1.1 * inch, stroke=1, fill=0)

    p.showPage()
    p.save()
    buffer.seek(0)
    return send_file(buffer, as_attachment=True, download_name=f"cleared_checks_{transaction_id}.pdf", mimetype='application/pdf')


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