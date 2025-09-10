# website/config.py

import os
from dotenv import load_dotenv
import re
import pytz # For timezone handling

# Load environment variables from a .env file if it exists
basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(basedir, '.env'))

class Config:
    """Base configuration class."""
    SECRET_KEY = os.environ.get('FLASK_SECRET_KEY', 'default-insecure-secret-key-for-dev')
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY', 'default-insecure-jwt-secret-key-for-dev')
    
    # MongoDB Configuration
    MONGO_URI = os.environ.get('MONGO_URI', "mongodb://localhost:27017/")
    MONGO_DB_NAME = os.environ.get('MONGO_DB_NAME', "deco_db")
    
    # Email Configuration
    MAIL_SERVER = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
    MAIL_PORT = int(os.environ.get('MAIL_PORT', 587))
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'True').lower() in ('true', '1', 'yes')
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME', 'wonderweeb15@gmail.com')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD', 'qcgx xawr tpos onva')
    MAIL_DEFAULT_SENDER = (os.environ.get('MAIL_DEFAULT_SENDER_NAME', 'DecoOffice'), 
                           os.environ.get('MAIL_DEFAULT_SENDER_EMAIL', 'wonderweeb15@gmail.com'))

    # JWT Configuration
    JWT_TOKEN_LOCATION = ["cookies"]
    JWT_COOKIE_SECURE = os.environ.get('JWT_COOKIE_SECURE', 'False').lower() in ('true', '1', 'yes')
    JWT_COOKIE_SAMESITE = os.environ.get('JWT_COOKIE_SAMESITE', 'Lax')
    JWT_COOKIE_CSRF_PROTECT = True
    JWT_CSRF_CHECK_FORM = True

    # Flask-Limiter Configuration
    LIMITER_STORAGE_URI = f"{MONGO_URI}{MONGO_DB_NAME}_limiter" # Use same DB for limiter data
    LIMITER_DEFAULT_LIMITS = ["200 per day", "50 per hour"]
    LIMITER_API_LIMITS = ["100 per hour", "10 per minute"]
    LIMITER_HEADERS_ENABLED = True
    LIMITER_STRATEGY = "fixed-window"

    # Security Configurations
    BAD_USER_AGENTS = [
        re.compile(r'python-requests', re.IGNORECASE),
        re.compile(r'scraperbot', re.IGNORECASE),
        re.compile(r'curl', re.IGNORECASE),
    ]
    
    # Talisman Configuration
    TALISMAN_FORCE_HTTPS = JWT_COOKIE_SECURE # Force HTTPS if JWT cookies are secure
    TALISMAN_FRAME_OPTIONS = 'DENY' 
    TALISMAN_X_CONTENT_TYPE_OPTIONS = True 

    # CSP Rules for Talisman
    CSP_RULES = {
        'default-src': "'self'",
        'script-src': "'self' 'unsafe-inline' https://cdn.tailwindcss.com https://cdnjs.cloudflare.com",
        'style-src': "'self' 'unsafe-inline' https://cdnjs.cloudflare.com https://fonts.googleapis.com",
        'font-src': "'self' https://fonts.gstatic.com https://cdnjs.cloudflare.com",
        'img-src': "'self' data:",
        'connect-src': "'self'", # Allow self for API calls
    }

class DevelopmentConfig(Config):
    """Development configuration - overrides defaults with development settings."""
    DEBUG = True
    TESTING = False

class TestingConfig(Config):
    """Testing configuration."""
    TESTING = True
    MONGO_DB_NAME = "deco_db_test" 
    LIMITER_STORAGE_URI = f"{Config.MONGO_URI}{MONGO_DB_NAME}_limiter"
    SECRET_KEY = 'test-insecure-secret-key' 
    JWT_SECRET_KEY = 'test-insecure-jwt-secret-key'

class ProductionConfig(Config):
    """Production configuration."""
    DEBUG = False
    TESTING = False
    JWT_COOKIE_SECURE = True 
    SESSION_COOKIE_SECURE = True 

config_by_name = dict(
    dev=DevelopmentConfig,
    test=TestingConfig,
    prod=ProductionConfig
)