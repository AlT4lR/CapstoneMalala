# website/__init__.py

# --- THIS IS THE FIX ---
import os
from flask import Flask, request, render_template
from pymongo import MongoClient
from flask_mail import Mail
from flask_jwt_extended import JWTManager
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import logging
from logging.config import dictConfig
from flask_talisman import Talisman
from pymongo.errors import OperationFailure
from flask_wtf.csrf import CSRFProtect

from .config import config_by_name
# --- FIX: Make sure all necessary functions are listed here ---
from .models import (
    get_user_by_username, get_user_by_email, add_user, check_password, update_last_login,
    record_failed_login_attempt, set_user_otp, verify_user_otp,
    add_schedule, get_schedules_by_date_range, get_all_categories, add_category,
    add_transaction, get_transactions_by_status, delete_transaction, get_transaction_by_id,
    # --- THIS IS THE FIX ---
    add_invoice
)

log_config = dict({
    'version': 1, 'disable_existing_loggers': False,
    'formatters': {'standard': {'format': '%(asctime)s [%(levelname)s] %(name)s: %(message)s'}},
    'handlers': {'console': {'level': 'INFO', 'formatter': 'standard', 'class': 'logging.StreamHandler', 'stream': 'ext://sys.stdout'}},
    'loggers': {
        '': {'handlers': ['console'], 'level': 'INFO', 'propagate': True},
        'pymongo': {'handlers': ['console'], 'level': 'WARNING', 'propagate': False},
    }
})
dictConfig(log_config)
logger = logging.getLogger(__name__)

mail = Mail()
jwt = JWTManager()
limiter = Limiter(key_func=get_remote_address, default_limits=["200 per day", "50 per hour"])
talisman = Talisman()
csrf = CSRFProtect()

def create_app(config_name='dev'):
    app = Flask(__name__)
    app.config.from_object(config_by_name[config_name])

    # --- THIS IS THE FIX ---
    # Ensure the upload folder exists before handling any requests
    if not os.path.exists(app.config['UPLOAD_FOLDER']):
        os.makedirs(app.config['UPLOAD_FOLDER'])

    mail.init_app(app)
    jwt.init_app(app)
    limiter.init_app(app)
    talisman.init_app(app, content_security_policy=app.config['CSP_RULES'])
    csrf.init_app(app)

    # Attach model functions to the app instance
    app.get_user_by_username = get_user_by_username
    app.get_user_by_email = get_user_by_email
    app.add_user = add_user
    app.check_password = check_password
    app.update_last_login = update_last_login
    app.record_failed_login_attempt = record_failed_login_attempt
    app.set_user_otp = set_user_otp
    app.verify_user_otp = verify_user_otp
    app.add_schedule = add_schedule
    app.get_schedules_by_date_range = get_schedules_by_date_range
    app.get_all_categories = get_all_categories
    app.add_category = add_category
    app.add_transaction = add_transaction
    app.get_transactions_by_status = get_transactions_by_status
    app.delete_transaction = delete_transaction
    app.get_transaction_by_id = get_transaction_by_id
    # --- THIS IS THE FIX ---
    app.add_invoice = add_invoice
    app.mail = mail

    # MongoDB Connection
    try:
        mongo_client = MongoClient(app.config['MONGO_URI'])
        app.db = mongo_client.get_database(app.config['MONGO_DB_NAME'])
        mongo_client.admin.command('ping')
        logger.info(f"Successfully connected to MongoDB: {app.config['MONGO_DB_NAME']}")
        
        users_collection = app.db.users
        try:
            users_collection.create_index(
                [('username', 1)], unique=True, name="username_1_case_insensitive_unique", 
                collation={'locale': 'en', 'strength': 2}
            )
            logger.info("Ensured unique index on 'users.username'.")
        except OperationFailure as e:
            if e.code in [85, 86]: logger.warning(f"Could not create index on username: {e.details['errmsg']}")
            else: raise
        try:
            users_collection.create_index(
                [('email', 1)], unique=True, name="email_1_case_insensitive_unique", 
                collation={'locale': 'en', 'strength': 2}
            )
            logger.info("Ensured unique index on 'users.email'.")
        except OperationFailure as e:
            if e.code in [85, 86]: logger.warning(f"Could not create index on email: {e.details['errmsg']}")
            else: raise
        
        app.db.transactions.create_index([
            ("username", 1), ("branch", 1), ("status", 1), ("datetime_utc", -1)
        ])
        logger.info("Ensured index on 'transactions'.")
    except Exception as e:
        logger.error(f"MongoDB connection or setup failed: {e}", exc_info=True)
        app.db = None
    
    # Register Blueprints
    from .auth import auth as auth_blueprint
    app.register_blueprint(auth_blueprint, url_prefix='/auth')
    from .views import main as main_blueprint
    app.register_blueprint(main_blueprint)

    # Error Handlers
    @app.errorhandler(404)
    def page_not_found(e):
        return render_template('errors/404.html'), 404
    @app.errorhandler(500)
    def internal_server_error(e):
        return render_template('errors/500.html'), 500

    return app