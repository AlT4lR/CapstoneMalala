# website/views/transactions.py

from flask import render_template, request, redirect, url_for, session, flash, jsonify, send_file, abort, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.platypus import Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_RIGHT
from reportlab.platypus.tables import Table, TableStyle
import io
import os
import logging

from . import main
from ..forms import TransactionForm, EditTransactionForm
from ..models import (
    log_user_activity, add_transaction, get_transactions_by_status, 
    get_transaction_by_id, get_child_transactions_by_parent_id,
    mark_folder_as_paid, archive_transaction, update_transaction,
    update_child_transaction
)

logger = logging.getLogger(__name__)

# --- API endpoint for the overview modal ---
@main.route('/api/transactions/overview/<transaction_id>', methods=['GET'])
@jwt_required()
def get_transaction_overview(transaction_id):
    username = get_jwt_identity()
    
    # 1. Fetch the parent folder
    folder = get_transaction_by_id(username, transaction_id, full_document=True)
    if not folder:
        return jsonify({'error': 'Transaction not found'}), 404
        
    # 2. Fetch all child checks
    child_checks = get_child_transactions_by_parent_id(username, transaction_id)
    
    # 3. Calculate summaries
    total_countered_check = sum(check.get('countered_check', 0) for check in child_checks)
    total_ewt = sum(check.get('ewt', 0) for check in child_checks)
    folder_amount = folder.get('amount', 0)
    remaining_balance = folder_amount - total_countered_check
    
    # 4. Serialize child_checks data for JSON response
    serialized_children = []
    for check in child_checks:
        serialized_children.append({
            'name': check.get('name', 'N/A'),
            'check_no': check.get('check_no', 'N/A'),
            'check_amount': check.get('check_amount', 0),
            'countered_check': check.get('countered_check', 0),
            'notes': check.get('notes', 'N/A'),
            'deductions': check.get('deductions', []),
            'ewt': check.get('ewt', 0)
        })

    # 5. Package and return the final data
    overview_data = {
        'folder_name': folder.get('name', 'N/A'),
        'child_checks': serialized_children,
        'summaries': {
            'total_ewt': total_ewt,
            'total_check_amount_to_pay': folder_amount,
            'total_countered_check': total_countered_check,
            'remaining_balance': remaining_balance
        }
    }
    return jsonify(overview_data)


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

    for check in child_checks:
        if not check.get('check_no') or check.get('check_amount', 0) == 0:
            check['is_incomplete'] = True

    total_countered_check = sum(check.get('countered_check', 0) for check in child_checks)
    total_ewt = sum(check.get('ewt', 0) for check in child_checks)
    folder_amount = folder.get('amount', 0)
    remaining_balance = folder_amount - total_countered_check
    
    return render_template(
        'transaction_folder_detail.html',
        folder=folder,
        child_checks=child_checks,
        form=form,
        total_countered_check=total_countered_check,
        total_ewt=total_ewt,
        remaining_balance=remaining_balance,
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

@main.route('/api/transactions/update/<transaction_id>', methods=['POST'])
@jwt_required()
def update_transaction_folder_route(transaction_id):
    """API route to update an existing transaction FOLDER."""
    username = get_jwt_identity()
    # Request.form contains the name, check_date, and due_date fields
    form_data = request.form.to_dict()
    
    if update_transaction(username, transaction_id, form_data):
        log_user_activity(username, f'Updated transaction folder details')
        return jsonify({'success': True}), 200
    else:
        return jsonify({'success': False, 'error': 'Failed to update folder or folder not found.'}), 400


@main.route('/add-transaction', methods=['POST'])
@jwt_required()
def add_transaction_route():
    username = get_jwt_identity()
    selected_branch = session.get('selected_branch')
    form = TransactionForm(request.form)
    parent_id = request.form.get('parent_id')
    
    if parent_id:
        form_data = request.form.to_dict()
        deductions = []
        deduction_names = request.form.getlist('deduction_name[]')
        deduction_amounts = request.form.getlist('deduction_amount[]')
        for name, amount_str in zip(deduction_names, deduction_amounts):
            if name and amount_str:
                try:
                    deductions.append({'name': name, 'amount': float(amount_str)})
                except ValueError: continue
        
        if form_data.get('ewt'):
            try:
                ewt_amount = float(form_data.get('ewt'))
                if ewt_amount > 0: deductions.append({'name': 'EWT', 'amount': ewt_amount})
            except ValueError: pass
                
        form_data['deductions'] = deductions
        
        if add_transaction(username, selected_branch, form_data, parent_id=parent_id):
            flash('Successfully added a new check!', 'success')
        else:
            flash('An error occurred while saving the check.', 'error')
        return redirect(url_for('main.transaction_folder_details', transaction_id=parent_id))

    if form.validate_on_submit():
        if add_transaction(username, selected_branch, form.data):
            flash('Successfully created a new transaction folder!', 'success')
            return jsonify({'success': True, 'redirect_url': url_for('main.transactions')})
        else:
            flash('An error occurred while saving the folder.', 'error')
            return jsonify({'success': False, 'error': 'Database error'}), 500
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({'success': False, 'errors': form.errors}), 400
    
    for field, errors in form.errors.items():
        for error in errors: flash(error, 'error')
    
    redirect_url = url_for('main.transaction_folder_details', transaction_id=parent_id) if parent_id else url_for('main.transactions')
    return redirect(redirect_url)

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
        return jsonify({'success': False, 'error': 'Invalid request data.'}), 400

    notes = data.get('notes')
    if mark_folder_as_paid(username, folder_id, notes):
        log_user_activity(username, f'Marked transaction folder as Paid')
        flash('Transaction successfully marked as Paid!', 'success')
        return jsonify({'success': True})
    else:
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
    total_folder_amount = folder.get('amount', 0.0)

    buffer = io.BytesIO()
    p = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter
    
    margin = 0.75 * inch
    bottom_margin = 1.0 * inch
    
    def draw_page_header():
        p.setFont("Helvetica-Bold", 16)
        p.drawCentredString(width / 2.0, height - 0.75 * inch, "CLEARED ISSUED CHECKS")
        
        try:
            logo_path = os.path.join(current_app.root_path, 'static', 'imgs', 'icons', 'Cleared_check_logo.png')
            if os.path.exists(logo_path):
                p.drawImage(logo_path, width - 2.0 * inch, height - 1.8 * inch, width=1.2*inch, height=1.2*inch, preserveAspectRatio=True, mask='auto')
        except Exception as e:
            logger.error(f"Could not draw logo on PDF: {e}")

        p.setFont("Helvetica", 11)
        p.drawString(margin, height - 1.25 * inch, "DECOLORES RETAIL CORPORATION")
        p.drawString(margin, height - 1.45 * inch, f"#{str(folder.get('_id'))}")
        folder_name = folder.get('name', 'N/A')
        p.drawString(margin, height - 1.65 * inch, folder_name)
        name_width = p.stringWidth(folder_name, "Helvetica", 11)
        p.line(margin, height - 1.67 * inch, margin + name_width, height - 1.67 * inch)
        paid_date = folder.get('paidAt').strftime('%B %d, %Y') if folder.get('paidAt') else 'N/A'
        p.drawString(margin, height - 1.85 * inch, paid_date)
        p.line(margin, height - 2.1 * inch, width - margin, height - 2.1 * inch)

    def draw_table_header(y_pos):
        p.setFont("Helvetica-Bold", 8)
        headers = ["Name Issued Check", "Check No.", "Date", "Check Amt", "EWT", "Other Ded.", "Countered Check"]
        col_x = [margin, 2.2*inch, 3.2*inch, 4.0*inch, 5.0*inch, 6.0*inch, 7.0*inch]
        for i, header in enumerate(headers):
            p.drawString(col_x[i], y_pos, header)
        p.line(margin, y_pos - 5, width - margin, y_pos - 5)
        return y_pos - 20

    draw_page_header()
    y_pos = height - 2.5 * inch
    y_pos = draw_table_header(y_pos)

    p.setFont("Helvetica", 8)
    for check in child_checks:
        check_row_start_y = y_pos

        if check_row_start_y - 30 < bottom_margin + 1.0 * inch: 
            p.showPage()
            draw_page_header()
            check_row_start_y = height - 2.5 * inch
            check_row_start_y = draw_table_header(check_row_start_y)
            y_pos = check_row_start_y

        notes = check.get('notes', '')
        
        col_x = [margin, 2.2*inch, 3.2*inch, 4.0*inch, 5.0*inch, 6.0*inch, 7.0*inch]
        
        p.drawString(col_x[0], y_pos, check.get('name', ''))
        p.drawString(col_x[1], y_pos, check.get('check_no', ''))
        p.drawString(col_x[2], y_pos, check.get('check_date').strftime('%m/%d/%y') if check.get('check_date') else '')
        
        other_deductions = sum(d['amount'] for d in check.get('deductions', []) if d['name'].upper() != 'EWT')
        
        p.drawRightString(col_x[4] - 0.05 * inch, y_pos, f"{check.get('check_amount', 0):,.2f}")
        p.drawRightString(col_x[5] - 0.05 * inch, y_pos, f"{check.get('ewt', 0):,.2f}")
        p.drawRightString(col_x[6] - 0.05 * inch, y_pos, f"{other_deductions:,.2f}")
        p.drawRightString(width - margin, y_pos, f"{check.get('countered_check', 0):,.2f}")
        
        y_pos -= 15
        
        if notes:
            p.setFont("Helvetica-Oblique", 7)
            p.drawString(margin + 5, y_pos, f"Notes: {notes}")
            y_pos -= 15
        
        p.line(margin, y_pos - 2, width - margin, y_pos - 2)
        y_pos -= 5
        
        p.setFont("Helvetica", 8)

    summary_table_y = bottom_margin + 0.1 * inch 
    summary_table_x = width - 3.8 * inch
    
    summary_data = [
        ['Countered Checks', f"₱ {total_countered_check:,.2f}"],
        ['Check Amount', f"₱ {total_folder_amount:,.2f}"]
    ]
    
    summary_table_style = TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
        ('FONTNAME', (0, 0), (0, 0), 'Helvetica'),
        ('FONTNAME', (0, 1), (0, 1), 'Helvetica-Bold'),
        ('FONTNAME', (1, 0), (1, 1), 'Helvetica-Bold'),
        ('BACKGROUND', (1, 0), (1, 1), colors.white),
        ('BOX', (1, 0), (1, 1), 1, colors.black),
        ('GRID', (1, 0), (1, 1), 0.5, colors.black),
        ('LEFTPADDING', (0, 0), (-1, -1), 2),
        ('RIGHTPADDING', (0, 0), (-1, -1), 4),
    ])

    summary_table = Table(summary_data, colWidths=[2.0 * inch, 1.75 * inch])
    summary_table.setStyle(summary_table_style)

    summary_table.wrapOn(p, width, height)
    summary_table.drawOn(p, summary_table_x, summary_table_y)
    
    p.showPage()
    p.save()
    buffer.seek(0)
    return send_file(buffer, as_attachment=True, download_name=f"cleared_checks_{transaction_id}.pdf", mimetype='application/pdf')

@main.route('/api/transactions/child/update/<transaction_id>', methods=['POST'])
@jwt_required()
def update_child_transaction_route(transaction_id):
    username = get_jwt_identity()
    form_data = request.form.to_dict()
    deductions = []
    deduction_names = request.form.getlist('deduction_name[]')
    deduction_amounts = request.form.getlist('deduction_amount[]')
    
    # Process deductions list
    for name, amount_str in zip(deduction_names, deduction_amounts):
        if name and amount_str:
            try:
                deductions.append({'name': name, 'amount': float(amount_str)})
            except ValueError: continue
    
    # Process EWT if present
    if form_data.get('ewt'):
        try:
            ewt_amount = float(form_data.get('ewt'))
            if ewt_amount > 0: deductions.append({'name': 'EWT', 'amount': ewt_amount})
        except ValueError: pass
    
    form_data['deductions'] = deductions

    # --- START OF MODIFICATION: Validation for Negative Countered Check ---
    try:
        check_amount = float(form_data.get('check_amount') or 0.0)
        total_deductions = sum(d['amount'] for d in deductions)
        
        if total_deductions > check_amount:
            diff = total_deductions - check_amount
            return jsonify({
                'success': False, 
                'error': f'Total deductions (₱{total_deductions:,.2f}) exceed Check Amount (₱{check_amount:,.2f}) by ₱{diff:,.2f}. Please adjust EWT or other deductions.'
            }), 400
    except ValueError:
        return jsonify({'success': False, 'error': 'Invalid numeric values provided.'}), 400
    # --- END OF MODIFICATION ---
    
    if update_child_transaction(username, transaction_id, form_data):
        flash('Issued check updated successfully!', 'success')
        return jsonify({'success': True})
    else:
        return jsonify({'success': False, 'error': 'Database update failed.'}), 500