# website/views/transactions.py

from flask import render_template, request, redirect, url_for, session, flash, jsonify, send_file, abort, current_app, make_response
from flask_jwt_extended import jwt_required, get_jwt_identity
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.platypus import Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_RIGHT, TA_CENTER
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
    update_child_transaction, get_user_by_username
)

logger = logging.getLogger(__name__)

# --- All routes before download_transaction_pdf are unchanged ---

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
    total_ewt = sum(check.get('ewt', 0) for check in child_checks)
    
    folder_amount = sum(check.get('check_amount', 0) for check in child_checks)
    folder['amount'] = folder_amount 
    
    remaining_balance = folder_amount - total_countered_check
    
    for check in child_checks:
        check['is_incomplete'] = (
            not check.get('check_no') or
            not check.get('check_amount') or
            check.get('countered_check') is None or float(check.get('countered_check')) == 0.0
        )
    
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
                except ValueError:
                    continue
        
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
    user = get_user_by_username(username)
    user_name = user.get('name', username).title() if user else username.title()
    
    folder = get_transaction_by_id(username, transaction_id, full_document=True)
    if not folder or folder.get('status') != 'Paid':
        abort(404)

    child_checks = get_child_transactions_by_parent_id(username, transaction_id)
    
    total_check_amount = sum(check.get('check_amount', 0) for check in child_checks)
    total_countered_check = sum(check.get('countered_check', 0) for check in child_checks)
    total_ewt = sum(check.get('ewt', 0) for check in child_checks)

    buffer = io.BytesIO()
    p = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter
    
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name='RightAlign', parent=styles['Normal'], alignment=TA_RIGHT, fontSize=8))
    styles.add(ParagraphStyle(name='NormalLeft', parent=styles['Normal'], fontSize=8))
    styles.add(ParagraphStyle(name='HeaderWhite', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=8, textColor=colors.whitesmoke, alignment=TA_CENTER))

    # --- Header Section ---
    p.setFont("Helvetica-Bold", 16)
    p.drawCentredString(width / 2.0, height - 0.75 * inch, "CLEARED ISSUED CHECKS")

    try:
        logo_path = os.path.join(current_app.root_path, 'static', 'imgs', 'icons', 'Cleared_check_logo.png')
        if os.path.exists(logo_path):
            # --- START OF CHANGE: Lowered the Y-coordinate for the logo ---
            p.drawImage(logo_path, width - 2.0 * inch, height - 1.7 * inch, width=1.2*inch, height=1.2*inch, preserveAspectRatio=True, mask='auto')
            # --- END OF CHANGE ---
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
    
    # --- Table Data Preparation ---
    header1 = ['Name Issued Check', 'Check No.', 'EWT', 'Check Amount', 'Countered Check', 'Notes', Paragraph('Deduction', styles['HeaderWhite'])]
    header2 = ['', '', '', '', '', '', 'Name', 'Amount']
    
    table_data = [header1, header2]

    for check in child_checks:
        deductions = check.get('deductions', [])
        notes_paragraph = Paragraph(check.get('notes', '').replace('\n', '<br/>'), styles['NormalLeft'])

        if not deductions:
            row_data = [
                Paragraph(check.get('name', ''), styles['NormalLeft']), check.get('check_no', ''),
                Paragraph(f"{check.get('ewt', 0):,.2f}", styles['RightAlign']),
                Paragraph(f"{check.get('check_amount', 0):,.2f}", styles['RightAlign']),
                Paragraph(f"{check.get('countered_check', 0):,.2f}", styles['RightAlign']),
                notes_paragraph, '', ''
            ]
            table_data.append(row_data)
        else:
            for i, deduction in enumerate(deductions):
                if i == 0:
                    row_data = [
                        Paragraph(check.get('name', ''), styles['NormalLeft']), check.get('check_no', ''),
                        Paragraph(f"{check.get('ewt', 0):,.2f}", styles['RightAlign']),
                        Paragraph(f"{check.get('check_amount', 0):,.2f}", styles['RightAlign']),
                        Paragraph(f"{check.get('countered_check', 0):,.2f}", styles['RightAlign']),
                        notes_paragraph,
                        Paragraph(deduction.get('name', ''), styles['NormalLeft']),
                        Paragraph(f"{deduction.get('amount', 0):,.2f}", styles['RightAlign'])
                    ]
                else:
                    row_data = ['', '', '', '', '', '', Paragraph(deduction.get('name', ''), styles['NormalLeft']), Paragraph(f"{deduction.get('amount', 0):,.2f}", styles['RightAlign'])]
                table_data.append(row_data)

    while len(table_data) < 15:
        table_data.append(["", "", "", "", "", "", "", ""])

    # --- Table Creation and Styling ---
    col_widths = [1.5*inch, 0.8*inch, 0.7*inch, 0.8*inch, 1.0*inch, 1.0*inch, 0.8*inch, 0.6*inch]
    tbl = Table(table_data, colWidths=col_widths, repeatRows=2)
    style = TableStyle([
        ('BACKGROUND', (0,0), (-1,1), colors.HexColor("#3a4d39")),
        ('TEXTCOLOR', (0,0), (-1,1), colors.whitesmoke),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('FONTNAME', (0,0), (-1,1), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,-1), 8),
        ('GRID', (0,0), (-1,-1), 1, colors.black),
        ('SPAN', (6,0), (7,0)),
        ('SPAN', (0,0), (0,1)), ('SPAN', (1,0), (1,1)), ('SPAN', (2,0), (2,1)),
        ('SPAN', (3,0), (3,1)), ('SPAN', (4,0), (4,1)), ('SPAN', (5,0), (5,1)),
        ('ALIGN', (0,2), (0,-1), 'LEFT'),
        ('ALIGN', (5,2), (5,-1), 'LEFT'),
        ('ALIGN', (6,2), (6,-1), 'LEFT'),
    ])
    tbl.setStyle(style)

    table_width, table_height = tbl.wrapOn(p, width, height)
    y_pos = height - 2.3 * inch - table_height
    tbl.drawOn(p, 0.5 * inch, y_pos)

    # --- Summary Section ---
    summary_y_start = y_pos - 0.5 * inch
    p.setFont("Helvetica", 10)
    
    p.drawRightString(width - 2.5 * inch, summary_y_start, "EWT")
    p.rect(width - 2.3 * inch, summary_y_start - 0.15*inch, 1.5*inch, 0.25*inch)
    p.drawRightString(width - 0.9 * inch, summary_y_start, f"■ {total_ewt:,.2f}")

    summary_y_start -= 0.35 * inch
    p.drawRightString(width - 2.5 * inch, summary_y_start, "Check Amount")
    p.rect(width - 2.3 * inch, summary_y_start - 0.15*inch, 1.5*inch, 0.25*inch)
    p.drawRightString(width - 0.9 * inch, summary_y_start, f"■ {total_check_amount:,.2f}")

    summary_y_start -= 0.35 * inch
    p.drawRightString(width - 2.5 * inch, summary_y_start, "Countered Checks")
    p.rect(width - 2.3 * inch, summary_y_start - 0.15*inch, 1.5*inch, 0.25*inch)
    p.drawRightString(width - 0.9 * inch, summary_y_start, f"■ {total_countered_check:,.2f}")

    # --- Signature Line ---
    p.line(0.75 * inch, 1.25 * inch, width - 4.0 * inch, 1.25 * inch)
    
    x_start = 0.75 * inch
    y_level = 1.1 * inch
    
    p.setFont("Helvetica-Bold", 10)
    label_text = "Prepared by: "
    p.drawString(x_start, y_level, label_text)
    
    label_width = p.stringWidth(label_text, "Helvetica-Bold", 10)
    
    p.setFont("Helvetica", 10)
    p.drawString(x_start + label_width, y_level, user_name)

    p.showPage()
    p.save()
    buffer.seek(0)
    
    response = make_response(send_file(
        buffer,
        as_attachment=True,
        download_name=f"cleared_checks_{transaction_id}.pdf",
        mimetype='application/pdf'
    ))
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response

@main.route('/api/transactions/child/update/<transaction_id>', methods=['POST'])
@jwt_required()
def update_child_transaction_route(transaction_id):
    username = get_jwt_identity()
    form_data = request.form.to_dict()
    deductions = []
    deduction_names = request.form.getlist('deduction_name[]')
    deduction_amounts = request.form.getlist('deduction_amount[]')
    
    for name, amount_str in zip(deduction_names, deduction_amounts):
        if name and amount_str:
            try:
                deductions.append({'name': name, 'amount': float(amount_str)})
            except ValueError:
                continue
    
    form_data['deductions'] = deductions
    
    if update_child_transaction(username, transaction_id, form_data):
        flash('Issued check updated successfully!', 'success')
        return jsonify({'success': True})
    else:
        return jsonify({'success': False, 'error': 'Database update failed.'}), 500