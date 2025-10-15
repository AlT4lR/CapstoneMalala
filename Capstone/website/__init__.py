# website/__init__.py
import os
from flask import Flask, render_template
from flask_mail import Mail
from flask_jwt_extended import JWTManager
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import logging
from logging.config import dictConfig
from flask_talisman import Talisman
from pymongo import MongoClient
from pymongo.errors import OperationFailure
from flask_wtf.csrf import CSRFProtect

from .config import config_by_name
from .models import (
    get_user_by_username, get_user_by_email, add_user, check_password, update_last_login,
    record_failed_login_attempt, set_user_otp, verify_user_otp, update_user_password,
    add_transaction, get_transactions_by_status, get_transaction_by_id,
    archive_transaction, get_archived_items,
    get_analytics_data,
    log_user_activity, get_recent_activity,
    add_invoice, get_invoices, get_invoice_by_id, archive_invoice,
    add_notification, get_unread_notifications, get_unread_notification_count, mark_notifications_as_read, save_push_subscription,
    add_loan,
    add_schedule, 
    get_schedules,
    # --- START OF MODIFICATION ---
    restore_item, delete_item_permanently
    # --- END OF MODIFICATION ---
    get_schedules
    get_schedules,
    # --- START OF MODIFICATION ---
    restore_item, delete_item_permanently
    # --- END OF MODIFICATION ---
)

# Logging configuration
log_config = {
    'version': 1, 'disable_existing_loggers': False,
    'formatters': {'standard': {'format': '%(asctime)s [%(levelname)s] %(name)s: %(message)s'}},
    'handlers': {'console': {'level': 'INFO', 'formatter': 'standard', 'class': 'logging.StreamHandler', 'stream': 'ext://sys.stdout'}},
    'loggers': {
        '': {'handlers': ['console'], 'level': 'INFO', 'propagate': True},
        'pymongo': {'handlers': ['console'], 'level': 'WARNING', 'propagate': False},
    }
}
dictConfig(log_config)
logger = logging.getLogger(__name__)

# Initialize extensions
mail = Mail()
jwt = JWTManager()
limiter = Limiter(key_func=get_remote_address, default_limits=["200 per day", "50 per hour"])
csrf = CSRFProtect()

def create_app(config_name='dev'):
    """Application factory function."""
    app = Flask(__name__)
    app.config.from_object(config_by_name[config_name])

    if not os.path.exists(app.config['UPLOAD_FOLDER']):
        os.makedirs(app.config['UPLOAD_FOLDER'])

    mail.init_app(app)
    jwt.init_app(app)
    limiter.init_app(app)
    csrf.init_app(app)

    # Attach all model functions to the app instance
    app.get_user_by_username = get_user_by_username
    app.get_user_by_email = get_user_by_email
    app.add_user = add_user
    app.check_password = check_password
    app.update_last_login = update_last_login
    app.record_failed_login_attempt = record_failed_login_attempt
    app.set_user_otp = set_user_otp
    app.verify_user_otp = verify_user_otp
    app.update_user_password = update_user_password
    
    app.add_transaction = add_transaction
    app.get_transactions_by_status = get_transactions_by_status
    app.get_transaction_by_id = get_transaction_by_id
    app.archive_transaction = archive_transaction
    app.get_archived_items = get_archived_items

    app.get_analytics_data = get_analytics_data
    
    app.log_user_activity = log_user_activity
    app.get_recent_activity = get_recent_activity

    app.add_invoice = add_invoice
    app.get_invoices = get_invoices
    app.get_invoice_by_id = get_invoice_by_id
    app.archive_invoice = archive_invoice

    app.add_notification = add_notification
    app.get_unread_notifications = get_unread_notifications
    app.get_unread_notification_count = get_unread_notification_count
    app.mark_notifications_as_read = mark_notifications_as_read
    app.save_push_subscription = save_push_subscription
    app.mail = mail
    
    app.add_loan = add_loan
    app.add_schedule = add_schedule
    app.get_schedules = get_schedules
    
    # --- START OF MODIFICATION ---
    app.restore_item = restore_item
    app.delete_item_permanently = delete_item_permanently
    # --- END OF MODIFICATION ---

    
    # --- START OF MODIFICATION ---
    app.restore_item = restore_item
    app.delete_item_permanently = delete_item_permanently
    # --- END OF MODIFICATION ---


    # MongoDB Connection
    try:
        mongo_client = MongoClient(app.config['MONGO_URI'])
        app.db = mongo_client.get_database(app.config['MONGO_DB_NAME'])
        mongo_client.admin.command('ping')
        logger.info(f"Successfully connected to MongoDB.")
    except Exception as e:
        logger.error(f"MongoDB connection failed: {e}", exc_info=True)
        app.db = None
    
    # Register Blueprints
    from .auth import auth as auth_blueprint
    app.register_blueprint(auth_blueprint, url_prefix='/auth')
    from .views import main as main_blueprint
    app.register_blueprint(main_blueprint)

    # Error Handlers
    @app.errorhandler(404)
    def page_not_found(e):
        return "404 Not Found", 404
    @app.errorhandler(500)
    def internal_server_error(e):
        return "500 Internal Server Error", 500

    return app