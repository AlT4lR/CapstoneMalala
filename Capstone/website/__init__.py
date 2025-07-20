# website/__init__.py

from flask import Flask
from pymongo import MongoClient
from flask_mail import Mail  # Import Flask-Mail

# This variable will hold our database connection
db = None
# This variable will hold our Mail instance
mail = None

def create_app():
    """
    Factory function to create and configure the Flask application.
    """
    app = Flask(__name__)
    
    app.config['SECRET_KEY'] = 'walang-kwenta-isa-naming-kagrupo'
    
    # --- MongoDB Configuration ---
    app.config['MONGO_URI'] = "mongodb://localhost:27017/"
    app.config['MONGO_DB_NAME'] = "deco_db"

    # --- Email (Flask-Mail) Configuration - REPLACE WITH YOUR CREDENTIALS ---
    app.config['MAIL_SERVER'] = 'smtp.gmail.com'  # e.g., 'smtp.gmail.com' for Gmail
    app.config['MAIL_PORT'] = 587
    app.config['MAIL_USE_TLS'] = True
    app.config['MAIL_USERNAME'] = 'your-email@example.com'  # Your email address
    app.config['MAIL_PASSWORD'] = 'your-email-app-password'  # Your email password or app-specific password
    app.config['MAIL_DEFAULT_SENDER'] = ('DecoOffice', 'your-email@example.com')

    global db, mail
    # FIX: Ensure mail is initialized after 'global mail'
    mail = Mail(app) # Initialize Mail with the app

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