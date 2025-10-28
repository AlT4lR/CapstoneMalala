# website/__init__.py
import os
from flask import Flask, render_template
from flask_mail import Mail
from flask_jwt_extended import JWTManager, get_jwt_identity
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import logging
from logging.config import dictConfig
from flask_talisman import Talisman
from pymongo import MongoClient
from pymongo.errors import OperationFailure
from flask_wtf.csrf import CSRFProtect

from .config import config_by_name
from .models.user import *
from .models.transaction import *
from .models.invoice import *
from .models.loan import *
from .models.schedule import *
from .models.activity import *
from .models.notification import *
from .models.analytics import *
from .models.archive import *

log_config = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {'standard': {'format': '%(asctime)s [%(levelname)s] %(name)s: %(message)s'}},
    'handlers': {'console': {'level': 'INFO', 'formatter': 'standard', 'class': 'logging.StreamHandler', 'stream': 'ext://sys.stdout'}},
    'loggers': {
        '': {'handlers': ['console'], 'level': 'INFO', 'propagate': True},
        'pymongo': {'handlers': ['console'], 'level': 'WARNING', 'propagate': False}
    }
}
dictConfig(log_config)
logger = logging.getLogger(__name__)

mail = Mail()
jwt = JWTManager()
limiter = Limiter(key_func=get_remote_address, default_limits=["200 per day", "50 per hour"])
csrf = CSRFProtect()

def create_app(config_name='dev'):
    app = Flask(__name__)
    app.config.from_object(config_by_name[config_name])

    # --- START OF MODIFICATION ---
    # Define and create the folder for avatar uploads
    app.config['AVATARS_FOLDER'] = os.path.join(app.root_path, '..', 'uploads', 'avatars')
    if not os.path.exists(app.config['AVATARS_FOLDER']):
        os.makedirs(app.config['AVATARS_FOLDER'])
    # --- END OF MODIFICATION ---
    
    if not os.path.exists(app.config['UPLOAD_FOLDER']):
        os.makedirs(app.config['UPLOAD_FOLDER'])
    if not os.path.exists(app.config['PROFILE_PIC_FOLDER']):
        os.makedirs(app.config['PROFILE_PIC_FOLDER'])

    mail.init_app(app)
    jwt.init_app(app)
    limiter.init_app(app)
    csrf.init_app(app)

    @app.context_processor
    def inject_user():
        try:
            username = get_jwt_identity()
            if username:
                user_data = get_user_by_username(username)
                return dict(current_user_data=user_data)
        except Exception:
            pass
        return dict(current_user_data=None)

    # -------------------------------
    # Attach model functions to app
    # -------------------------------
    app.get_user_by_username = get_user_by_username
    app.get_user_by_email = get_user_by_email
    app.add_user = add_user
    app.check_password = check_password
    app.update_last_login = update_last_login
    app.record_failed_login_attempt = record_failed_login_attempt
    app.set_user_otp = set_user_otp
    app.verify_user_otp = verify_user_otp
    app.update_user_password = update_user_password
    app.save_push_subscription = save_push_subscription
    app.get_user_push_subscriptions = get_user_push_subscriptions
    app.update_personal_info = update_personal_info
    app.update_profile_picture = update_profile_picture # <-- ADDED LINE

    app.add_transaction = add_transaction
    app.get_transactions_by_status = get_transactions_by_status
    app.get_transaction_by_id = get_transaction_by_id
    app.update_transaction = update_transaction
    app.archive_transaction = archive_transaction
    app.get_child_transactions_by_parent_id = get_child_transactions_by_parent_id
    app.mark_folder_as_paid = mark_folder_as_paid

    app.get_analytics_data = get_analytics_data
    app.get_weekly_billing_summary = get_weekly_billing_summary

    # --- START OF MODIFICATION (Activity Log) ---
    app.log_user_activity = log_user_activity
    app.get_recent_activity = get_recent_activity
    # --- END OF MODIFICATION ---

    app.add_invoice = add_invoice
    app.get_invoices = get_invoices
    app.get_invoice_by_id = get_invoice_by_id
    app.archive_invoice = archive_invoice

    app.add_notification = add_notification
    app.get_notifications = get_notifications
    app.get_unread_notification_count = get_unread_notification_count
    app.mark_single_notification_as_read = mark_single_notification_as_read

    app.add_loan = add_loan
    app.get_loans = get_loans

    app.add_schedule = add_schedule
    app.get_schedules = get_schedules
    app.update_schedule = update_schedule
    app.delete_schedule = delete_schedule

    app.get_archived_items = get_archived_items
    app.restore_item = restore_item
    app.delete_item_permanently = delete_item_permanently

    app.mail = mail

    try:
        mongo_client = MongoClient(app.config['MONGO_URI'])
        app.db = mongo_client.get_database(app.config['MONGO_DB_NAME'])
        mongo_client.admin.command('ping')
        logger.info("Successfully connected to MongoDB.")
    except Exception as e:
        logger.error(f"MongoDB connection failed: {e}", exc_info=True)
        app.db = None

    from .auth import auth as auth_blueprint
    app.register_blueprint(auth_blueprint, url_prefix='/auth')

    from .views import main as main_blueprint
    app.register_blueprint(main_blueprint)

    @app.errorhandler(404)
    def page_not_found(e):
        return render_template('errors/404.html'), 404

    @app.errorhandler(500)
    def internal_server_error(e):
        return render_template('errors/500.html'), 500

    return app