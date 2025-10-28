# website/utils/email_utils.py

import logging
import os
from flask import current_app, render_template, url_for
from datetime import datetime
import sib_api_v3_sdk
from sib_api_v3_sdk.rest import ApiException

logger = logging.getLogger(__name__)

def send_email_via_api(recipient_email, subject, html_content):
    """
    Sends an email using the Brevo (Sendinblue) API.
    Returns True on success, False on failure.
    """
    brevo_api_key = current_app.config.get('BREVO_API_KEY')
    sender_email = current_app.config.get('MAIL_DEFAULT_SENDER_EMAIL')
    sender_name = current_app.config.get('MAIL_DEFAULT_SENDER_NAME')

    # --- START OF TEMPORARY DEBUGGING ---
    # This will print the API key that the application is ACTUALLY using to the Render logs.
    # We can use this to confirm if it's loading the new key correctly.
    print(f"DEBUG: Attempting to send email. Using Brevo API Key: '{brevo_api_key}'")
    # --- END OF TEMPORARY DEBUGGING ---

    if not all([brevo_api_key, sender_email, sender_name]):
        logger.error("Brevo API Key or sender info is not configured. Cannot send email.")
        return False

    configuration = sib_api_v3_sdk.Configuration()
    configuration.api_key['api-key'] = brevo_api_key
    api_instance = sib_api_v3_sdk.TransactionalEmailsApi(sib_api_v3_sdk.ApiClient(configuration))

    send_smtp_email = sib_api_v3_sdk.SendSmtpEmail(
        to=[{"email": recipient_email}],
        sender={"email": sender_email, "name": sender_name},
        subject=subject,
        html_content=html_content
    )

    try:
        api_response = api_instance.send_transac_email(send_smtp_email)
        logger.info(f"Successfully sent email to {recipient_email} via Brevo API. Message ID: {api_response.message_id}")
        return True
    except ApiException as e:
        logger.error(f"Failed to send email to {recipient_email} via Brevo API. Body: {e.body}", exc_info=True)
        return False

def send_notification_email(recipient_email, subject, title, message, url):
    """
    Constructs an email from a template and sends it using the Brevo API.
    """
    render_url = os.environ.get('RENDER_EXTERNAL_URL', None)
    base_url = render_url or url_for('main.root_route', _external=True)
    full_url = f"{base_url.rstrip('/')}{url}" if url else None

    try:
        html_body = render_template(
            'emails/notification_email.html',
            title=title,
            message=message,
            url=full_url,
            now=datetime.utcnow()
        )
        return send_email_via_api(recipient_email, subject, html_body)
    except Exception as e:
        logger.error(f"Failed to render or send notification email to {recipient_email}: {e}", exc_info=True)
        return False