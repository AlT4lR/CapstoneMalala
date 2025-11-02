# website/config.py

import os
from dotenv import load_dotenv
from datetime import timedelta

basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(basedir, '..', '.env'))

class Config:
    """Base configuration class."""
    SECRET_KEY = os.environ.get('FLASK_SECRET_KEY', 'a_very_secret_key_that_should_be_changed')
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY', 'a_super_secret_jwt_key_to_change')
    
    UPLOAD_FOLDER = os.path.join(basedir, '..', 'uploads', 'invoices')
    PROFILE_PIC_FOLDER = os.path.join(basedir, '..', 'uploads', 'profile_pics')

    # VAPID Keys
    VAPID_PRIVATE_KEY = os.environ.get('VAPID_PRIVATE_KEY')
    VAPID_PUBLIC_KEY = os.environ.get('VAPID_PUBLIC_KEY')
    VAPID_CLAIM_EMAIL = os.environ.get('VAPID_CLAIM_EMAIL')
    
    # MongoDB Settings
    MONGO_URI = os.environ.get('MONGO_URI', "mongodb://localhost:2717/")
    MONGO_DB_NAME = os.environ.get('MONGO_DB_NAME', "deco_db")
    
    # Brevo API Key for sending emails via HTTP
    BREVO_API_KEY = os.environ.get('BREVO_API_KEY')
    
    # Legacy/Fallback SMTP settings
    MAIL_SERVER = os.environ.get('MAIL_SERVER')
    MAIL_PORT = int(os.environ.get('MAIL_PORT', 587))
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'False').lower() in ('true', '1', 'yes')
    MAIL_USE_SSL = os.environ.get('MAIL_USE_SSL', 'False').lower() in ('true', '1', 'yes')
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER_NAME = os.environ.get('MAIL_DEFAULT_SENDER_NAME', 'DecoOffice')
    MAIL_DEFAULT_SENDER_EMAIL = os.environ.get('MAIL_DEFAULT_SENDER_EMAIL', 'no-reply@decooffice.com')

    # JWT Settings
    JWT_TOKEN_LOCATION = ["cookies"]
    JWT_COOKIE_SECURE = False
    JWT_COOKIE_CSRF_PROTECT = False
    
    # --- START OF MODIFICATION: Change token expiration (Merged) ---
    # The original value was timedelta(hours=1)
    # This new value sets the session to last for 30 days.
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(days=30)
    # --- END OF MODIFICATION (Merged) ---

class DevelopmentConfig(Config):
    DEBUG = True

class ProductionConfig(Config):
    DEBUG = False
    JWT_COOKIE_SECURE = True 

config_by_name = dict(
    dev=DevelopmentConfig,
    prod=ProductionConfig
)