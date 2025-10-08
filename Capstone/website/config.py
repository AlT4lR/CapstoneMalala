# website/config.py
import os
from dotenv import load_dotenv
import re
from datetime import timedelta

basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(basedir, '..', '.env'))

class Config:
    """Base configuration class."""
    SECRET_KEY = os.environ.get('FLASK_SECRET_KEY', 'a_very_secret_key_that_should_be_changed')
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY', 'a_super_secret_jwt_key_to_change')

    UPLOAD_FOLDER = os.path.join(basedir, '..', 'uploads', 'invoices')

    # PWA Push Notification VAPID Keys
    VAPID_PRIVATE_KEY = os.environ.get('VAPID_PRIVATE_KEY')
    VAPID_PUBLIC_KEY = os.environ.get('VAPID_PUBLIC_KEY')
    VAPID_CLAIM_EMAIL = os.environ.get('VAPID_CLAIM_EMAIL')

    # MongoDB Configuration
    MONGO_URI = os.environ.get('MONGO_URI', "mongodb://localhost:27017/")
    MONGO_DB_NAME = os.environ.get('MONGO_DB_NAME', "deco_db")

    # Email Configuration
    MAIL_SERVER = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
    MAIL_PORT = int(os.environ.get('MAIL_PORT', 587))
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'True').lower() in ('true', '1', 'yes')
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = (
        os.environ.get('MAIL_DEFAULT_SENDER_NAME', 'DecoOffice'),
        os.environ.get('MAIL_DEFAULT_SENDER_EMAIL', 'no-reply@decooffice.com')
    )

    # Zoho API Configuration
    ZOHO_CLIENT_ID = os.environ.get('ZOHO_CLIENT_ID')
    ZOHO_CLIENT_SECRET = os.environ.get('ZOHO_CLIENT_SECRET')
    ZOHO_REDIRECT_URI = os.environ.get('ZOHO_REDIRECT_URI', 'http://127.0.0.1:5000/zoho/callback')
    ZOHO_API_BASE_URL = "https://calendar.zoho.com/api/v1"
    ZOHO_ACCOUNTS_BASE_URL = "https://accounts.zoho.com/oauth/v2"

    # JWT Configuration
    JWT_TOKEN_LOCATION = ["cookies"]
    JWT_COOKIE_SECURE = os.environ.get('JWT_COOKIE_SECURE', 'False').lower() in ('true', '1', 'yes')
    JWT_COOKIE_SAMESITE = os.environ.get('JWT_COOKIE_SAMESITE', 'Lax')
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=1)
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=30)
    JWT_CSRF_CHECK_FORM = True
    JWT_CSRF_IN_COOKIES = True
    JWT_COOKIE_CSRF_PROTECT = False

    # Flask-Limiter
    LIMITER_STORAGE_URI = f"{MONGO_URI}{MONGO_DB_NAME}_limiter"

    # --- THIS IS THE FIX ---
    # The Content Security Policy is now correctly configured to allow all necessary CDN scripts.
    CSP_RULES = {
        'default-src': "'self'",
        'script-src': [
            "'self'",
            "'unsafe-inline'",
            "https://cdn.tailwindcss.com",
            "https://cdn.jsdelivr.net",
            "https://cdnjs.cloudflare.com"
        ],
        'style-src': "'self' 'unsafe-inline' https://cdnjs.cloudflare.com https://fonts.googleapis.com https://cdn.jsdelivr.net",
        'font-src': "'self' data: https://fonts.gstatic.com https://cdnjs.cloudflare.com",
        'img-src': "'self' data:",
        'connect-src': "'self'",
    }


class DevelopmentConfig(Config):
    DEBUG = True
    TESTING = False

class TestingConfig(Config):
    TESTING = True
    MONGO_DB_NAME = "deco_db_test"
    LIMITER_STORAGE_URI = f"{Config.MONGO_URI}{MONGO_DB_NAME}_limiter"
    SECRET_KEY = 'test-insecure-secret-key'
    JWT_SECRET_KEY = 'test-insecure-jwt-secret-key'
    WTF_CSRF_ENABLED = False

class ProductionConfig(Config):
    DEBUG = False
    TESTING = False
    JWT_COOKIE_SECURE = True
    SESSION_COOKIE_SECURE = True

config_by_name = dict(
    dev=DevelopmentConfig,
    test=TestingConfig,
    prod=ProductionConfig
)