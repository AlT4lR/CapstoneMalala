# website/__init__.py

from flask import Flask
from pymongo import MongoClient

# This variable will hold our database connection
db = None

def create_app():
    """
    Factory function to create and configure the Flask application.
    """
    app = Flask(__name__)
    
    app.config['SECRET_KEY'] = 'a-temporary-secret-key-for-development'
    
    app.config['MONGO_URI'] = "mongodb://localhost:27017/"
    app.config['MONGO_DB_NAME'] = "deco_db"

    global db
    try:
        mongo_client = MongoClient(app.config['MONGO_URI'])
        db = mongo_client.get_database(app.config['MONGO_DB_NAME'])
        mongo_client.admin.command('ping')
        
        # FIXED: Removed emoji from the print statement
        print(f"[SUCCESS] Successfully connected to MongoDB database: {app.config['MONGO_DB_NAME']}")

        users_collection = db.users
        users_collection.create_index([('username', 1)], unique=True, background=True)
        users_collection.create_index([('email', 1)], unique=True, background=True)
        
        # FIXED: Removed emoji from the print statement
        print("[SUCCESS] Ensured unique indexes on 'users' collection.")

    except Exception as e:
        # FIXED: Removed emoji from the print statement
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