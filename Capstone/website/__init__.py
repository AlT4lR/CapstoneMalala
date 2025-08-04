# website/__init__.py

from flask import Flask
from pymongo import MongoClient
from flask_mail import Mail
from flask_jwt_extended import JWTManager
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import os
import logging
from logging.config import dictConfig

# Configure logging
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
        '': {  # Root logger
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': True
        },
        'flask': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False
        },
        'pymongo': {
            'handlers': ['console'],
            'level': 'WARNING', # PyMongo can be verbose, set to WARNING
            'propagate': False
        },
        'werkzeug': { # For Werkzeug debugger/server logs
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False
        }
    }
})
dictConfig(log_config)
logger = logging.getLogger(__name__)


# Flask extensions will be initialized within create_app and attached to app
mail = Mail()
jwt = JWTManager()
limiter = Limiter()

def create_app():
    """
    Factory function to create and configure the Flask application.
    """
    app = Flask(__name__)
    
    # --- Security & Secret Keys ---
    app.config['SECRET_KEY'] = os.environ.get('FLASK_SECRET_KEY', 'default-insecure-secret-key-for-dev')
    app.config['JWT_SECRET_KEY'] = os.environ.get('JWT_SECRET_KEY', 'default-insecure-jwt-secret-key-for-dev')
    
    # --- MongoDB Configuration ---
    app.config['MONGO_URI'] = os.environ.get('MONGO_URI', "mongodb://localhost:27017/")
    app.config['MONGO_DB_NAME'] = os.environ.get('MONGO_DB_NAME', "deco_db")

    # --- Email (Flask-Mail) Configuration ---
    app.config['MAIL_SERVER'] = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
    app.config['MAIL_PORT'] = int(os.environ.get('MAIL_PORT', 587))
    app.config['MAIL_USE_TLS'] = os.environ.get('MAIL_USE_TLS', 'True').lower() in ('true', '1', 'yes')
    app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME', 'wonderweeb15@gmail.com')
    app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD', 'qcgx xawr tpos onva')
    app.config['MAIL_DEFAULT_SENDER'] = (os.environ.get('MAIL_DEFAULT_SENDER_NAME', 'DecoOffice'), 
                                         os.environ.get('MAIL_DEFAULT_SENDER_EMAIL', 'wonderweeb15@gmail.com'))

    # --- JWT Configuration ---
    app.config["JWT_TOKEN_LOCATION"] = ["cookies"]
    app.config["JWT_COOKIE_SECURE"] = os.environ.get('JWT_COOKIE_SECURE', 'False').lower() in ('true', '1', 'yes')
    app.config["SESSION_COOKIE_SECURE"] = app.config["JWT_COOKIE_SECURE"]
    app.config["JWT_COOKIE_SAMESITE"] = os.environ.get('JWT_COOKIE_SAMESITE', 'Lax')
    app.config["JWT_COOKIE_CSRF_PROTECT"] = True
    app.config["JWT_CSRF_CHECK_FORM"] = True

    # --- Flask-Limiter Configuration ---
    limiter_db_name = os.environ.get('MONGO_DB_NAME', "deco_db") + "_limiter"
    app.config["LIMITER_STORAGE_URI"] = f"{app.config['MONGO_URI']}{limiter_db_name}"
    app.config["LIMITER_DEFAULT_LIMITS"] = ["200 per day", "50 per hour"]
    app.config["LIMITER_HEADERS_ENABLED"] = True
    app.config["LIMITER_STRATEGY"] = "fixed-window" # Explicitly set a strategy

    # Initialize extensions with the app
    mail.init_app(app)
    jwt.init_app(app)
    limiter.init_app(app, key_func=get_remote_address, default_limits=app.config["LIMITER_DEFAULT_LIMITS"], storage_uri=app.config["LIMITER_STORAGE_URI"], headers_enabled=app.config["LIMITER_HEADERS_ENABLED"], strategy=app.config["LIMITER_STRATEGY"])

    # Attach DB to app context for easier access
    try:
        if not app.config['MONGO_URI']:
            raise ValueError("MONGO_URI is not configured.")
            
        mongo_client = MongoClient(app.config['MONGO_URI'])
        app.db = mongo_client.get_database(app.config['MONGO_DB_NAME'])
        
        # Verify connection
        mongo_client.admin.command('ping')
        logger.info(f"Successfully connected to MongoDB database: {app.config['MONGO_DB_NAME']}")

        # Index creation (consider a more robust migration strategy for production)
        users_collection = app.db.users
        users_collection.create_index([('username', 1)], unique=True, background=True, 
                                      collation={'locale': 'en', 'strength': 2}) # Case-insensitive unique index
        users_collection.create_index([('email', 1)], unique=True, background=True, 
                                      collation={'locale': 'en', 'strength': 2}) # Case-insensitive unique index
        logger.info("Ensured unique indexes on 'users' collection (case-insensitive).")

    except ValueError as ve:
        logger.error(f"MongoDB configuration error: {ve}")
        app.db = None # Ensure app.db is None if config fails
    except Exception as e:
        logger.error(f"Could not connect to MongoDB or create indexes: {e}")
        app.db = None

    # --- Register Blueprints ---
    from .auth import auth as auth_blueprint
    app.register_blueprint(auth_blueprint, url_prefix='/') # url_prefix is optional here

    from .views import main as main_blueprint
    app.register_blueprint(main_blueprint, url_prefix='/')
    
    return app

# Removed global get_db, get_mail, get_jwt, get_limiter functions.
# Extensions are now accessed via current_app or app.extension_name.