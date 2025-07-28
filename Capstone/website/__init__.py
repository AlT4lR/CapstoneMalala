# website/__init__.py

from flask import Flask
from pymongo import MongoClient
from flask_mail import Mail
from flask_jwt_extended import JWTManager
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import os

# This variable will hold our database connection
db = None
# This variable will hold our Mail instance
mail = None
# This variable will hold our JWTManager instance
jwt = None
# This variable will hold our Limiter instance
limiter = None

def create_app():
    """
    Factory function to create and configure the Flask application.
    """
    app = Flask(__name__)
    
    app.config['SECRET_KEY'] = os.environ.get('FLASK_SECRET_KEY', 'walang-kwenta-isa-naming-kagrupo-default-secret')
    
    # --- MongoDB Configuration ---
    app.config['MONGO_URI'] = os.environ.get('MONGO_URI', "mongodb://localhost:27017/")
    app.config['MONGO_DB_NAME'] = os.environ.get('MONGO_DB_NAME', "deco_db")

    # --- Email (Flask-Mail) Configuration - NOW HARDCODED FOR LOCAL TESTING ---
    app.config['MAIL_SERVER'] = 'smtp.gmail.com'
    app.config['MAIL_PORT'] = 587
    app.config['MAIL_USE_TLS'] = True
    app.config['MAIL_USERNAME'] = 'wonderweeb15@gmail.com'  # <--- Dont change this
    app.config['MAIL_PASSWORD'] = 'qcgx xawr tpos onva'  # Dont change 
    app.config['MAIL_DEFAULT_SENDER'] = ('DecoOffice', 'wonderweeb15@gmail.com') # <--- Dont change this

    # --- JWT Configuration ---
    app.config["JWT_SECRET_KEY"] = os.environ.get('JWT_SECRET_KEY', 'super-secret-jwt-key-change-this-in-prod')
    app.config["JWT_TOKEN_LOCATION"] = ["cookies"]
    
    # --- FIX STARTS HERE ---
    # For local development over HTTP, set this to False.
    # For production with HTTPS, this MUST be True.
    app.config["JWT_COOKIE_SECURE"] = False 
    # --- FIX ENDS HERE ---
    
    app.config["JWT_COOKIE_SAMESITE"] = os.environ.get('JWT_COOKIE_SAMESITE', 'Lax')
    app.config["JWT_COOKIE_CSRF_PROTECT"] = True
    app.config["JWT_CSRF_CHECK_FORM"] = True

    # --- Flask-Limiter Configuration ---
    app.config["LIMITER_STORAGE_URI"] = app.config['MONGO_URI'] + app.config['MONGO_DB_NAME'] + "_limiter"
    app.config["LIMITER_DEFAULT_LIMITS"] = ["200 per day", "50 per hour"]
    app.config["LIMITER_HEADERS_ENABLED"] = True

    global db, mail, jwt, limiter
    
    # Initialize extensions
    mail = Mail(app)
    jwt = JWTManager(app)
    limiter = Limiter(
        get_remote_address,
        app=app,
        default_limits=app.config["LIMITER_DEFAULT_LIMITS"],
        storage_uri=app.config["LIMITER_STORAGE_URI"],
        headers_enabled=app.config["LIMITER_HEADERS_ENABLED"]
    )

    try:
        mongo_client = MongoClient(app.config['MONGO_URI'])
        db = mongo_client.get_database(app.config['MONGO_DB_NAME'])
        mongo_client.admin.command('ping')
        
        print(f"[SUCCESS] Successfully connected to MongoDB database: {app.config['MONGO_DB_NAME']}")

        users_collection = db.users
        users_collection.create_index([('username', 1)], unique=True, background=True)
        users_collection.create_index([('email', 1)], unique=True, background=True)
        
        print("[SUCCESS] Ensured unique indexes on 'users' collection.")

    except Exception as e:
        print(f"[ERROR] Could not connect to MongoDB or create indexes: {e}")
        db = None

    from .auth import auth as auth_blueprint
    app.register_blueprint(auth_blueprint)

    from .views import main as main_blueprint
    app.register_blueprint(main_blueprint)
    
    return app

def get_db():
    """
    Helper function to give other files access to the database connection.
    """
    if db is None:
        print("[WARNING] MongoDB connection not initialized!")
    return db

def get_mail():
    """
    Helper function to give other files access to the Mail instance.
    """
    if mail is None:
        print("[WARNING] Flask-Mail not initialized!")
    return mail

def get_jwt():
    """
    Helper function to give other files access to the JWTManager instance.
    """
    if jwt is None:
        print("[WARNING] Flask-JWT-Extended not initialized!")
    return jwt

def get_limiter():
    """
    Helper function to give other files access to the Limiter instance.
    """
    if limiter is None:
        print("[WARNING] Flask-Limiter not initialized!")
    return limiter