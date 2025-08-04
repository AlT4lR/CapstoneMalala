# website/__init__.py

from flask import Flask, request, abort, g
from pymongo import MongoClient
from flask_mail import Mail
from flask_jwt_extended import JWTManager
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import os
import logging
from logging.config import dictConfig
import re
from flask_talisman import Talisman # Import Talisman
import pytz # For timezone handling

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
        'flask_talisman': { 'handlers': ['console'], 'level': 'WARNING', 'propagate': False } # Reduce Talisman verbosity if needed
    }
})
dictConfig(log_config)
logger = logging.getLogger(__name__)

# Flask extensions
mail = Mail()
jwt = JWTManager()
limiter = Limiter()
talisman = Talisman() # Initialize Talisman

# --- Security Configurations ---
# User Agent Filtering Patterns
BAD_USER_AGENTS = [
    re.compile(r'python-requests', re.IGNORECASE),
    re.compile(r'scraperbot', re.IGNORECASE),
    re.compile(r'curl', re.IGNORECASE),
]

def create_app():
    app = Flask(__name__)
    
    # --- Secret Keys & Security ---
    app.config['SECRET_KEY'] = os.environ.get('FLASK_SECRET_KEY', 'default-insecure-secret-key-for-dev')
    app.config['JWT_SECRET_KEY'] = os.environ.get('JWT_SECRET_KEY', 'default-insecure-jwt-secret-key-for-dev')
    
    # --- MongoDB Configuration ---
    app.config['MONGO_URI'] = os.environ.get('MONGO_URI', "mongodb://localhost:27017/")
    app.config['MONGO_DB_NAME'] = os.environ.get('MONGO_DB_NAME', "deco_db")

    # --- Email Configuration ---
    app.config['MAIL_SERVER'] = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
    app.config['MAIL_PORT'] = int(os.environ.get('MAIL_PORT', 587))
    app.config['MAIL_USE_TLS'] = os.environ.get('MAIL_USE_TLS', 'True').lower() in ('true', '1', 'yes')
    app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME', 'wonderweeb15@gmail.com')
    app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD', 'qcgx xawr tpos onva')
    app.config['MAIL_DEFAULT_SENDER'] = (os.environ.get('MAIL_DEFAULT_SENDER_NAME', 'DecoOffice'), 
                                         os.environ.get('MAIL_DEFAULT_SENDER_EMAIL', 'wonderweeb15@gmail.com'))

    # --- JWT Configuration ---
    app.config["JWT_TOKEN_LOCATION"] = ["cookies"]
    # Ensure JWT_COOKIE_SECURE is True in production (HTTPS)
    app.config["JWT_COOKIE_SECURE"] = os.environ.get('JWT_COOKIE_SECURE', 'False').lower() in ('true', '1', 'yes')
    app.config["SESSION_COOKIE_SECURE"] = app.config["JWT_COOKIE_SECURE"]
    app.config["JWT_COOKIE_SAMESITE"] = os.environ.get('JWT_COOKIE_SAMESITE', 'Lax')
    app.config["JWT_COOKIE_CSRF_PROTECT"] = True
    app.config["JWT_CSRF_CHECK_FORM"] = True

    # --- Flask-Limiter Configuration ---
    limiter_db_name = os.environ.get('MONGO_DB_NAME', "deco_db") + "_limiter"
    app.config["LIMITER_STORAGE_URI"] = f"{app.config['MONGO_URI']}{limiter_db_name}"
    app.config["LIMITER_DEFAULT_LIMITS"] = ["200 per day", "50 per hour"]
    app.config["LIMITER_API_LIMITS"] = ["100 per hour", "10 per minute"]
    app.config["LIMITER_HEADERS_ENABLED"] = True
    app.config["LIMITER_STRATEGY"] = "fixed-window"

    # --- Initialize Extensions ---
    mail.init_app(app)
    jwt.init_app(app)
    limiter.init_app(
        app,
        key_func=get_remote_address,
        default_limits=app.config["LIMITER_DEFAULT_LIMITS"],
        storage_uri=app.config["LIMITER_STORAGE_URI"],
        headers_enabled=app.config["LIMITER_HEADERS_ENABLED"],
        strategy=app.config["LIMITER_STRATEGY"]
    )
    
    # --- Content Security Policy (CSP) and other Security Headers ---
    # Configure CSP to allow specific resources
    csp_rules = {
        'default-src': "'self'",
        'script-src': "'self' 'unsafe-inline' https://cdn.tailwindcss.com https://cdnjs.cloudflare.com",
        'style-src': "'self' 'unsafe-inline' https://cdnjs.cloudflare.com https://fonts.googleapis.com",
        'font-src': "'self' https://fonts.gstatic.com https://cdnjs.cloudflare.com",
        'img-src': "'self' data:",
        'connect-src': "'self' https://api.example.com", # Example: if you call external APIs
        # Add other directives as needed
    }
    # Apply Talisman with CSP
    talisman.init_app(app, content_security_policy=csp_rules, 
                      force_https=app.config["JWT_COOKIE_SECURE"], # Force HTTPS if JWT cookies are secure
                      frame_options='DENY', # Prevent clickjacking
                      x_content_type_options=True) # Prevent MIME-sniffing

    # --- MongoDB Connection & Indexing ---
    try:
        if not app.config['MONGO_URI']:
            raise ValueError("MONGO_URI is not configured.")
            
        mongo_client = MongoClient(app.config['MONGO_URI'])
        app.db = mongo_client.get_database(app.config['MONGO_DB_NAME'])
        
        mongo_client.admin.command('ping')
        logger.info(f"Successfully connected to MongoDB database: {app.config['MONGO_DB_NAME']}")

        # Index creation (consider migrations for production)
        users_collection = app.db.users
        users_collection.create_index([('username', 1)], unique=True, background=True, 
                                      collation={'locale': 'en', 'strength': 2})
        users_collection.create_index([('email', 1)], unique=True, background=True, 
                                      collation={'locale': 'en', 'strength': 2})
        logger.info("Ensured unique indexes on 'users' collection (case-insensitive).")

    except ValueError as ve:
        logger.error(f"MongoDB configuration error: {ve}")
        app.db = None
    except Exception as e:
        logger.error(f"Could not connect to MongoDB or create indexes: {e}")
        app.db = None

    # --- Register Blueprints ---
    from .auth import auth as auth_blueprint
    app.register_blueprint(auth_blueprint, url_prefix='/')

    from .views import main as main_blueprint
    app.register_blueprint(main_blueprint, url_prefix='/')
    
    return app