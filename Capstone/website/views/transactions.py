# website/views/transactions.py

from flask import render_template, request, redirect, url_for, session, flash, jsonify, send_file, abort
from flask_jwt_extended import jwt_required, get_jwt_identity
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.platypus import Paragraph
from reportlab.lib.styles import getSampleStyleSheet
import io

from . import main # Import the blueprint
from ..forms import TransactionForm, EditTransactionForm
from ..models import (
    log_user_activity, add_transaction, get_transactions_by_status, 
    get_transaction_by_id, get_child_transactions_by_parent_id,
    mark_folder_as_paid, archive_transaction, update_transaction
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
    
    return render_template(
        'paid_transaction_folder_detail.html',
        folder=folder,
        child_checks=child_checks,
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
                return jsonify({'success': True, 'redirect_url': url_for('main.transactions_pending')})
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