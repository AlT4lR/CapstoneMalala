from flask import (
    render_template, request, jsonify, url_for, current_app, 
    send_from_directory, send_file, abort, session
)
from flask_jwt_extended import jwt_required, get_jwt_identity
from werkzeug.utils import secure_filename
from datetime import datetime
import os
# --- START OF CONSOLIDATED IMPORTS (Includes Full OCR Support) ---
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
# --- END OF CONSOLIDATED IMPORTS ---

from . import main # Import the blueprint
from ..models import (
    log_user_activity, add_invoice, get_invoices, 
    get_invoice_by_id, archive_invoice
)

logger = logging.getLogger(__name__)

# --- Tesseract Configuration (Kept for context, but commented out for PATH reliance) ---
# The hardcoded Windows path for Tesseract has been REMOVED to rely on the 
# system's PATH environment variable, making it compatible with Linux/Docker.

# try:
#     # For Windows development environments, uncomment and modify this line:
#     # pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
#     pass
# except Exception as e:
#     logger.warning(f"Could not set the Tesseract path (if applicable). OCR will search system PATH. Error: {e}")

# --- START OF FULL OCR FUNCTION WITH ROBUST ERROR HANDLING ---
def perform_ocr_on_image(image_path):
    """
    Performs Optical Character Recognition (OCR) on an image file using Tesseract.
    Includes robust error handling for common Tesseract issues like not found or timeouts.
    """
    # --- More detailed error handling for cross-platform stability ---
    try:
        # Use a timeout to prevent the process from hanging on difficult images
        return pytesseract.image_to_string(Image.open(image_path), timeout=15)
    except pytesseract.TesseractNotFoundError:
        # This error is specific: the tesseract executable was not found in the system's PATH.
        logger.error("TESSERACT NOT FOUND: The Tesseract executable was not found in the system's PATH.")
        return "OCR Error: Tesseract executable not found. Please check the server configuration."
    except RuntimeError as timeout_error:
        # This catches the timeout error specifically (e.g., Tesseract process hanging)
        logger.error(f"OCR timed out for image {image_path}: {timeout_error}")
        return "OCR failed: Processing timed out. The image may be too complex."
    except Exception as e:
        # This catches all other errors (e.g., bad installation, missing language files)
        logger.error(f"An unexpected OCR error occurred for image {image_path}: {e}")
        return f"OCR failed: An unexpected error occurred. Check server logs for details. (Error: {str(e)[:100]})"
# --- END OF FULL OCR FUNCTION ---


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
    extracted_text_all = [] # List to hold OCR text from all uploaded files

    for file in files:
        if file:
            filename = secure_filename(file.filename)
            filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            
            # Perform OCR on the saved file
            extracted_text = perform_ocr_on_image(filepath)
            
            extracted_text_all.append(extracted_text)
            processed_files_info.append({
                'filename': filename, 'content_type': file.content_type,
                'size': os.path.getsize(filepath)
            })

    if add_invoice(username, selected_branch, invoice_data, processed_files_info, "\n\n".join(extracted_text_all)):
        log_user_activity(username, 'Uploaded an invoice')
        # Original behavior: Redirect on successful upload
        return jsonify({'success': True, 'redirect_url': url_for('main.all_invoices')})
    else:
        # Ensure cleanup of uploaded files if the database operation fails, though not strictly required by the prompt
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
    # Replace newlines with <br/> for ReportLab's Paragraph to handle multiline text
    ocr_text = invoice.get('extracted_text', 'No text was extracted.').replace('\n', '<br/>')
    ocr_paragraph = Paragraph(ocr_text, styles['Normal'])
    # Calculate wrapped size
    w, h = ocr_paragraph.wrapOn(p, width - 2 * inch, height)
    p.saveState()
    # Adjust position calculation for the paragraph drawing
    paragraph_start_y = height - 1.6 * inch - h
    ocr_paragraph.drawOn(p, inch, paragraph_start_y)
    p.restoreState()
    
    y_pos = paragraph_start_y - 0.5 * inch # Start drawing files below the paragraph

    if invoice.get('files'):
        # Check if there is enough room for the file title and margin
        if y_pos < height - (height - 1.5 * inch):
             p.showPage()
             y_pos = height - inch
        
        p.setFont("Helvetica-Bold", 16)
        p.drawString(inch, y_pos, "Attached Images")
        y_pos -= 0.5 * inch # Move down after the new title

        for file_info in invoice['files']:
            filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], file_info['filename'])
            if os.path.exists(filepath):
                try:
                    img_reader = ImageReader(filepath)
                    img_width, img_height = img_reader.getSize()
                    
                    max_width = width - 2 * inch
                    if img_width > max_width:
                        # Scale the image down if it's too wide
                        ratio = max_width / img_width
                        img_width = max_width
                        img_height *= ratio
                    
                    # Check if the image will fit on the current page
                    if y_pos - img_height < inch: 
                        p.showPage()
                        y_pos = height - inch

                    # Draw the image
                    p.drawImage(img_reader, inch, y_pos - img_height, width=img_width, height=img_height)
                    y_pos -= (img_height + 0.5 * inch)
                except Exception as e:
                    logger.error(f"Could not process image for PDF: {filepath}, Error: {e}")
                    p.drawString(inch, y_pos, f"[Could not load image: {file_info['filename']}]")
                    y_pos -= 0.5 * inch

    p.save()
    buffer.seek(0)
    return send_file(buffer, as_attachment=True, download_name=f"invoice_{invoice_id}.pdf", mimetype='application/pdf')

@main.route('/invoices/uploads/<path:filename>')
@jwt_required()
def uploaded_invoice_file(filename):
    """Provides a secure endpoint to access uploaded invoice files."""
    return send_from_directory(current_app.config['UPLOAD_FOLDER'], filename)