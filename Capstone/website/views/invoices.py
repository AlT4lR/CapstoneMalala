from flask import (
    render_template, request, jsonify, url_for, current_app, 
    send_from_directory, send_file, abort, session, make_response
)
from flask_jwt_extended import jwt_required, get_jwt_identity
from werkzeug.utils import secure_filename
from datetime import datetime
import os
import pytesseract
from PIL import Image
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.utils import ImageReader
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph
from reportlab.lib.styles import getSampleStyleSheet
import io
import logging

from . import main # Import the blueprint
from ..models import (
    log_user_activity, add_invoice, get_invoices, 
    get_invoice_by_id, archive_invoice
)

logger = logging.getLogger(__name__)

def perform_ocr_on_image(image_path):
    """
    Performs Optical Character Recognition (OCR) on an image file using Tesseract.
    """
    try:
        return pytesseract.image_to_string(Image.open(image_path), timeout=15)
    except pytesseract.TesseractNotFoundError:
        logger.error("TESSERACT NOT FOUND: The Tesseract executable was not found in the system's PATH.")
        return "OCR Error: Tesseract executable not found. Please check the server configuration."
    except RuntimeError as timeout_error:
        logger.error(f"OCR timed out for image {image_path}: {timeout_error}")
        return "OCR failed: Processing timed out. The image may be too complex."
    except Exception as e:
        logger.error(f"An unexpected OCR error occurred for image {image_path}: {e}")
        return f"OCR failed: An unexpected error occurred. Check server logs for details. (Error: {str(e)[:100]})"

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

# --- Invoice API Routes ---
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

    try:
        date_obj = None
        date_str = request.form.get('date')
        if date_str:
            date_obj = datetime.strptime(date_str, '%Y-%m-%d')
    except ValueError:
        return jsonify({'success': False, 'error': 'Invalid date format. Please use YYYY-MM-DD.'}), 400

    invoice_data = {
        'folder_name': request.form.get('folder-name'),
        'category': request.form.get('categories'),
        'date': date_obj,
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

@main.route('/api/invoices/<invoice_id>/download', methods=['GET'])
@jwt_required()
def download_invoice_as_pdf(invoice_id):
    username = get_jwt_identity()
    invoice = get_invoice_by_id(username, invoice_id)
    if not invoice:
        abort(404)

    buffer = io.BytesIO()
    p = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter
    
    # --- PAGE 1: OFFICIAL RECEIPT DETAILS ---
    
    p.setFont("Helvetica-Bold", 16)
    p.drawCentredString(width / 2.0, height - 0.75 * inch, "OFFICIAL RECEIPT")

    # --- Logo ---
    try:
        logo_path = os.path.join(current_app.root_path, 'static', 'imgs', 'icons', 'Cleared_check_logo.png')
        if os.path.exists(logo_path):
            # --- START OF CHANGE: Lowered the Y-coordinate for the logo ---
            p.drawImage(logo_path, width - 2.0 * inch, height - 1.7 * inch, width=1.2*inch, height=1.2*inch, preserveAspectRatio=True, mask='auto')
            # --- END OF CHANGE ---
    except Exception as e:
        logger.error(f"Could not draw logo on PDF: {e}")

    # --- Corporation and Invoice Details ---
    p.setFont("Helvetica", 11)
    y_pos = height - 1.25 * inch
    p.drawString(0.75 * inch, y_pos, "DECOLORES RETAIL CORPORATION")
    y_pos -= 0.4 * inch

    label_x = 0.75 * inch
    value_x = 1.75 * inch

    p.setFont("Helvetica-Bold", 10)
    p.drawString(label_x, y_pos, "Folder Name")
    p.setFont("Helvetica", 10)
    p.drawString(value_x, y_pos, invoice.get('folder_name', 'N/A'))
    y_pos -= 0.25 * inch

    p.setFont("Helvetica-Bold", 10)
    p.drawString(label_x, y_pos, "Category")
    p.setFont("Helvetica", 10)
    p.drawString(value_x, y_pos, invoice.get('category', 'N/A'))
    y_pos -= 0.25 * inch
    
    p.setFont("Helvetica-Bold", 10)
    p.drawString(label_x, y_pos, "Date")
    p.setFont("Helvetica", 10)
    invoice_date = invoice.get('date')
    date_str = invoice_date.strftime('%B %d, %Y') if isinstance(invoice_date, datetime) else 'N/A'
    p.drawString(value_x, y_pos, date_str)
    y_pos -= 0.2 * inch 

    top_line_y = y_pos
    p.line(0.75 * inch, top_line_y, width - 0.75 * inch, top_line_y)
    
    bottom_line_y = 1.5 * inch
    p.line(0.75 * inch, bottom_line_y, width - 0.75 * inch, bottom_line_y)

    # --- IMAGE PLACEMENT LOGIC ---
    files = invoice.get('files', [])
    if files:
        # --- Draw the FIRST image on the first page ---
        first_file = files[0]
        filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], first_file['filename'])
        if os.path.exists(filepath):
            try:
                margin = 0.85 * inch 
                available_width = width - 2 * margin
                available_height = top_line_y - bottom_line_y - (0.2 * inch) 
                
                img_reader = ImageReader(filepath)
                img_width, img_height = img_reader.getSize()
                
                img_aspect = img_height / float(img_width) if img_width else 0
                frame_aspect = available_height / float(available_width) if available_width else 0
                
                if img_aspect > frame_aspect:
                    new_height = available_height
                    new_width = new_height / img_aspect
                else:
                    new_width = available_width
                    new_height = new_width * img_aspect
                    
                x_centered = (width - new_width) / 2
                y_centered = bottom_line_y + (available_height - new_height) / 2 + (0.1 * inch)
                
                p.drawImage(img_reader, x_centered, y_centered, width=new_width, height=new_height, preserveAspectRatio=True, mask='auto')

            except Exception as e:
                logger.error(f"Could not process first image for PDF: {filepath}, Error: {e}")
                p.drawCentredString(width / 2.0, (top_line_y + bottom_line_y) / 2, f"[Could not load image]")

        # --- Draw SUBSEQUENT images on new pages ---
        if len(files) > 1:
            page_margin = 1 * inch
            page_available_width = width - 2 * page_margin
            page_available_height = height - 2 * page_margin

            for file_info in files[1:]:
                filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], file_info['filename'])
                if os.path.exists(filepath):
                    try:
                        p.showPage()
                        img_reader = ImageReader(filepath)
                        img_width, img_height = img_reader.getSize()
                        
                        img_aspect = img_height / float(img_width)
                        frame_aspect = page_available_height / float(page_available_width)
                        
                        if img_aspect > frame_aspect:
                            new_height = page_available_height
                            new_width = new_height / img_aspect
                        else:
                            new_width = page_available_width
                            new_height = new_width * img_aspect
                            
                        x_centered = (width - new_width) / 2
                        y_centered = (height - new_height) / 2
                        
                        p.drawImage(img_reader, x_centered, y_centered, width=new_width, height=new_height, preserveAspectRatio=True, mask='auto')

                    except Exception as e:
                        logger.error(f"Could not process subsequent image for PDF: {filepath}, Error: {e}")
                        p.showPage()
                        p.drawCentredString(width / 2.0, height / 2.0, f"[Could not load image: {file_info['filename']}]")

    p.save()
    buffer.seek(0)
    
    response = make_response(send_file(
        buffer, 
        as_attachment=True, 
        download_name=f"official_receipt_{invoice_id}.pdf", 
        mimetype='application/pdf'
    ))
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response

@main.route('/invoices/uploads/<path:filename>')
@jwt_required()
def uploaded_invoice_file(filename):
    """Provides a secure endpoint to access uploaded invoice files."""
    return send_from_directory(current_app.config['UPLOAD_FOLDER'], filename)