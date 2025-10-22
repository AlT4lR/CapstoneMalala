# website/views/invoices.py

from flask import (
    render_template, request, jsonify, url_for, current_app, 
    send_from_directory, send_file, abort, session
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

# --- Tesseract Configuration ---
# Ensure this path is correct for your system.
try:
    pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
except Exception as e:
    logger.warning(f"Could not set the Tesseract path. OCR will likely fail. Error: {e}")


def perform_ocr_on_image(image_path):
    # --- START OF MODIFICATION: More detailed error handling ---
    try:
        # Use a timeout to prevent the process from hanging on difficult images
        return pytesseract.image_to_string(Image.open(image_path), timeout=15)
    except pytesseract.TesseractNotFoundError:
        # This error is specific: the tesseract.exe file was not found at the path.
        logger.error("TESSERACT NOT FOUND: The 'tesseract.exe' file was not found at the specified path.")
        return "OCR Error: Tesseract executable not found. Please check the server configuration."
    except RuntimeError as timeout_error:
        # This catches the timeout error specifically
        logger.error(f"OCR timed out for image {image_path}: {timeout_error}")
        return "OCR failed: Processing timed out. The image may be too complex."
    except Exception as e:
        # This catches all other errors (e.g., bad installation, missing language files)
        # and logs the actual error message for debugging.
        logger.error(f"An unexpected OCR error occurred for image {image_path}: {e}")
        return f"OCR failed: An unexpected error occurred. Check server logs for details. (Error: {str(e)[:100]})"
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
    styles = getSampleStyleSheet()
    
    p.setFont("Helvetica-Bold", 16)
    p.drawString(inch, height - inch, f"Invoice: {invoice.get('folder_name', 'N/A')}")
    
    p.setFont("Helvetica-Bold", 12)
    p.drawString(inch, height - 1.5 * inch, "Extracted Text (OCR)")
    ocr_text = invoice.get('extracted_text', 'No text was extracted.').replace('\n', '<br/>')
    ocr_paragraph = Paragraph(ocr_text, styles['Normal'])
    w, h = ocr_paragraph.wrapOn(p, width - 2 * inch, height)
    ocr_paragraph.drawOn(p, inch, height - 1.6 * inch - h)
    
    if invoice.get('files'):
        p.showPage() 
        p.setFont("Helvetica-Bold", 16)
        p.drawString(inch, height - inch, "Attached Images")
        y_pos = height - 1.5 * inch
        
        for file_info in invoice['files']:
            filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], file_info['filename'])
            if os.path.exists(filepath):
                try:
                    img_reader = ImageReader(filepath)
                    img_width, img_height = img_reader.getSize()
                    
                    max_width = width - 2 * inch
                    if img_width > max_width:
                        ratio = max_width / img_width
                        img_width = max_width
                        img_height *= ratio
                    
                    if y_pos - img_height < inch: 
                        p.showPage()
                        y_pos = height - inch

                    p.drawImage(img_reader, inch, y_pos - img_height, width=img_width, height=img_height)
                    y_pos -= (img_height + 0.5 * inch)
                except Exception as e:
                    logger.error(f"Could not process image for PDF: {filepath}, Error: {e}")
                    p.drawString(inch, y_pos, f"[Could not load image: {file_info['filename']}]")
                    y_pos -= 0.5*inch

    p.save()
    buffer.seek(0)
    return send_file(buffer, as_attachment=True, download_name=f"invoice_{invoice_id}.pdf", mimetype='application/pdf')

@main.route('/invoices/uploads/<path:filename>')
@jwt_required()
def uploaded_invoice_file(filename):
    """Provides a secure endpoint to access uploaded invoice files."""
    return send_from_directory(current_app.config['UPLOAD_FOLDER'], filename)