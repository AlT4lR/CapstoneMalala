# website/utils/email_utils.py

import logging
from flask import current_app, render_template
from flask_mail import Message
from datetime import datetime

logger = logging.getLogger(__name__)

def send_notification_email(recipient_email, subject, title, message, url):
    """
    Constructs and sends a notification email using a template.
    """
    mail = current_app.mail
    if not mail:
        logger.error("Flask-Mail is not initialized. Cannot send email.")
        return

    # Generate the full external URL for the email content
    full_url = f"{current_app.config.get('PREFERRED_URL_SCHEME', 'http')}://{current_app.config.get('SERVER_NAME', 'localhost')}{url}" if url else None

    try:
        html_body = render_template(
            'emails/notification_email.html',
            title=title,
            message=message,
            url=full_url,
            now=datetime.utcnow()
        )
        
        msg = Message(subject, recipients=[recipient_email], html=html_body)
        mail.send(msg)
        logger.info(f"Successfully sent notification email to {recipient_email}")

    except Exception as e:
        logger.error(f"Failed to send email to {recipient_email}: {e}", exc_info=True)