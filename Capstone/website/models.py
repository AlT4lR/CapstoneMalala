# website/models.py

from . import get_db
import bcrypt
from pymongo.errors import DuplicateKeyError
from datetime import datetime

def get_user_by_username(username):
    """Retrieves a user document from MongoDB by username."""
    mongo_db = get_db()
    
    # CORRECT: Check if the database object exists before using it.
    if mongo_db is not None:
        return mongo_db.users.find_one({'username': {'$regex': f'^{username}$', '$options': 'i'}})
    
    return None # Return None if there's no database connection

def add_user(username, email, password):
    """
    Adds a new user to MongoDB. Hashes password with bcrypt.
    Returns True on success, False on failure.
    """
    mongo_db = get_db()
    
    # CORRECT: The fix is right here.
    if mongo_db is not None:
        # Hash the password using bcrypt for strong security
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

        # Create the full user document matching our schema
        user_data = {
            'username': username,
            'email': email.lower(),
            'passwordHash': hashed_password,
            'role': 'user',
            'isActive': True,
            'lastLogin': None,
            'createdAt': datetime.utcnow(),
            'updatedAt': datetime.utcnow()
        }

        try:
            mongo_db.users.insert_one(user_data)
            print(f"Successfully registered user: {username}")
            return True
        except DuplicateKeyError:
            print(f"Registration failed: Username '{username}' or Email '{email}' already exists.")
            return False
        except Exception as e:
            print(f"Error adding user '{username}' to MongoDB: {e}")
            return False
            
    # If mongo_db IS None, we fall through to here
    return False

def check_password(stored_hash, provided_password):
    """Checks a provided password against a stored bcrypt hash."""
    return bcrypt.checkpw(provided_password.encode('utf-8'), stored_hash)

def update_last_login(username):
    """Updates the lastLogin timestamp for a user."""
    mongo_db = get_db()

    # CORRECT: Also apply the fix here.
    if mongo_db is not None:
        mongo_db.users.update_one(
            {'username': username},
            {'$set': {'lastLogin': datetime.utcnow(), 'updatedAt': datetime.utcnow()}}
        )