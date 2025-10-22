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

    VAPID_PRIVATE_KEY = os.environ.get('VAPID_PRIVATE_KEY')
    VAPID_PUBLIC_KEY = os.environ.get('VAPID_PUBLIC_KEY')
    VAPID_CLAIM_EMAIL = os.environ.get('VAPID_CLAIM_EMAIL')
    
    MONGO_URI = os.environ.get('MONGO_URI', "mongodb://localhost:27017/")
    MONGO_DB_NAME = os.environ.get('MONGO_DB_NAME', "deco_db")
    
    MAIL_SERVER = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
    MAIL_PORT = int(os.environ.get('MAIL_PORT', 587))
    
    # --- START OF MODIFICATION ---
    # The string 'True'/'true' from the .env file is converted to a boolean
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'True').lower() in ('true', '1', 'yes')
    MAIL_USE_SSL = os.environ.get('MAIL_USE_SSL', 'False').lower() in ('true', '1', 'yes')
    # --- END OF MODIFICATION ---
    
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = (os.environ.get('MAIL_DEFAULT_SENDER_NAME', 'DecoOffice'), 
                           os.environ.get('MAIL_DEFAULT_SENDER_EMAIL', 'no-reply@decooffice.com'))

    JWT_TOKEN_LOCATION = ["cookies"]
    JWT_COOKIE_SECURE = False
    JWT_COOKIE_CSRF_PROTECT = False
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=1)

class DevelopmentConfig(Config):
    DEBUG = True

class ProductionConfig(Config):
    DEBUG = False
    JWT_COOKIE_SECURE = True 

config_by_name = dict(
    dev=DevelopmentConfig,
    prod=ProductionConfig
)