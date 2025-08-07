# website/__init__.py

from flask import Flask, request, abort, g, render_template
from pymongo import MongoClient
from flask_mail import Mail
from flask_jwt_extended import JWTManager
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import os
import logging
from logging.config import dictConfig
import re
from flask_talisman import Talisman
from pymongo.errors import OperationFailure
# REMOVE: from flask_babel import Babel
from flask_wtf.csrf import CSRFProtect

# Import configuration settings
from .config import config_by_name

# Import model functions here so they can be attached to the app
from .models import (
    get_user_by_username, add_user, check_password, update_last_login,
    record_failed_login_attempt, set_user_otp, verify_user_otp,
    add_schedule, get_schedules_by_date_range, get_all_categories, add_category
)

# --- Logging Configuration ---
log_config = dict({
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'standard': {
            'format': '%(asctime)s [%(levelname)s] %(name)s: %(message)s'
        },
    },
    'handlers': {
        'console': {
            'level': 'INFO',
            'formatter': 'standard',
            'class': 'logging.StreamHandler',
            'stream': 'ext://sys.stdout',
        },
    },
    'loggers': {
        '': { 'handlers': ['console'], 'level': 'INFO', 'propagate': True },
        'flask': { 'handlers': ['console'], 'level': 'INFO', 'propagate': False },
        'pymongo': { 'handlers': ['console'], 'level': 'WARNING', 'propagate': False },
        'werkzeug': { 'handlers': ['console'], 'level': 'INFO', 'propagate': False },
        '__main__': { 'handlers': ['console'], 'level': 'INFO', 'propagate': False },
        'flask_talisman': { 'handlers': ['console'], 'level': 'WARNING', 'propagate': False }
    }
})
dictConfig(log_config)
logger = logging.getLogger(__name__)

# Initialize extensions outside the factory function
mail = Mail()
jwt = JWTManager()
limiter = Limiter(key_func=get_remote_address)
talisman = Talisman()
csrf = CSRFProtect()
# REMOVE: babel = Babel() # Remove Babel instance initialization

def create_app(config_name='dev'): # Default to development config
    """
    Flask application factory function.

    Creates and configures the Flask application instance based on the provided
    configuration name.

    Args:
        config_name (str): The name of the configuration to use (e.g., 'dev', 'prod').
                           Defaults to 'dev'.

    Returns:
        Flask: The configured Flask application instance.
    """
    app = Flask(__name__)

    # Load configuration from config object
    app.config.from_object(config_by_name[config_name])

    # --- Initialize Extensions with App ---
    mail.init_app(app)
    jwt.init_app(app)
    limiter.init_app(app)
    talisman.init_app(
        app,
        force_https=app.config.get("TALISMAN_FORCE_HTTPS", True), # Use .get for safer access
        frame_options=app.config.get("TALISMAN_FRAME_OPTIONS", "SAMEORIGIN"),
        x_content_type_options=app.config.get("TALISMAN_X_CONTENT_TYPE_OPTIONS", "nosniff"),
        content_security_policy=app.config.get("CSP_RULES")
    )
    csrf.init_app(app)
    # REMOVE: babel.init_app(app) # Remove Babel initialization

    # --- Babel Locale Selector ---
    # REMOVE this entire section as Babel is being removed
    # @babel.localeselector
    # def get_locale():
    #     # Try to get locale from user's browser preferences
    #     # Fallback to a default language if no match is found
    #     return request.accept_languages.best_match(['en', 'es'])
    # --- END Babel Locale Selector ---

    # --- Attach model functions to the app instance ---
    # ... (this part remains the same) ...
    app.get_user_by_username = get_user_by_username
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


    # --- MongoDB Connection & Indexing ---
    # ... (this part remains the same) ...
    try:
        if not app.config.get('MONGO_URI'): # Use .get for safer access
            raise ValueError("MONGO_URI is not configured.")

        mongo_client = MongoClient(app.config['MONGO_URI'])
        app.db = mongo_client.get_database(app.config['MONGO_DB_NAME'])

        # Test connection by pinging the server
        mongo_client.admin.command('ping')
        logger.info(f"Successfully connected to MongoDB database: {app.config['MONGO_DB_NAME']}")

        # Index creation
        users_collection = app.db.users
        try:
            users_collection.create_index(
                [('username', 1)],
                unique=True,
                background=True,
                collation={'locale': 'en', 'strength': 2},
                name="username_1_case_insensitive"
            )
            logger.info("Ensured unique index on 'users.username' (case-insensitive).")
        except OperationFailure as e:
            if e.code == 86: # IndexKeySpecsConflict
                logger.warning(f"Index 'username_1_case_insensitive' already exists or has a conflict: {e}")
            else:
                raise

        try:
            users_collection.create_index(
                [('email', 1)],
                unique=True,
                background=True,
                collation={'locale': 'en', 'strength': 2},
                name="email_1_case_insensitive"
            )
            logger.info("Ensured unique index on 'users.email' (case-insensitive).")
        except OperationFailure as e:
            if e.code == 86: # IndexKeySpecsConflict
                logger.warning(f"Index 'email_1_case_insensitive' already exists or has a conflict: {e}")
            else:
                raise

    except ValueError as ve:
        logger.error(f"MongoDB configuration error: {ve}")
        app.db = None
    except Exception as e:
        logger.error(f"An unexpected error occurred during MongoDB setup: {e}", exc_info=True)
        app.db = None

    # --- Register Blueprints ---
    # ... (this part remains the same) ...
    from .auth import auth as auth_blueprint
    app.register_blueprint(auth_blueprint, url_prefix='/auth')

    from .views import main as main_blueprint
    app.register_blueprint(main_blueprint, url_prefix='/')

    # --- Register Custom Error Handlers ---
    # ... (this part remains the same) ...
    @app.errorhandler(404)
    def page_not_found(e):
        logger.warning(f"404 Error encountered for URL: {request.url}")
        return render_template('errors/404.html'), 404

    @app.errorhandler(500)
    def internal_server_error(e):
        logger.error(f"500 Internal Server Error encountered: {e}", exc_info=True)
        return render_template('errors/500.html'), 500

    return app