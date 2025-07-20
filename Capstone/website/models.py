from . import get_db
import bcrypt
from pymongo.errors import DuplicateKeyError
from datetime import datetime, timedelta
import random
import string

def get_user_by_username(username):
    """Retrieves a user document from MongoDB by username."""
    mongo_db = get_db()
    
    if mongo_db is not None:
        return mongo_db.users.find_one({'username': {'$regex': f'^{username}$', '$options': 'i'}})
    
    return None

def add_user(username, email, password):
    """
    Adds a new user to MongoDB with isActive set to False.
    Returns True on success, False on failure.
    """
    mongo_db = get_db()
    
    if mongo_db is not None:
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

        user_data = {
            'username': username,
            'email': email.lower(),
            'passwordHash': hashed_password,
            'role': 'user',
            'isActive': False,  # User is inactive until OTP verification
            'otp': None,
            'otpExpiresAt': None,
            'lastLogin': None,
            'createdAt': datetime.utcnow(),
            'updatedAt': datetime.utcnow()
        }

        try:
            mongo_db.users.insert_one(user_data)
            print(f"Successfully registered user: {username}. Awaiting verification.")
            return True
        except DuplicateKeyError:
            print(f"Registration failed: Username '{username}' or Email '{email}' already exists.")
            return False
        except Exception as e:
            print(f"Error adding user '{username}' to MongoDB: {e}")
            return False
            
    return False

def check_password(stored_hash, provided_password):
    """Checks a provided password against a stored bcrypt hash."""
    return bcrypt.checkpw(provided_password.encode('utf-8'), stored_hash)

def update_last_login(username):
    """Updates the lastLogin timestamp for a user."""
    mongo_db = get_db()

    if mongo_db is not None:
        mongo_db.users.update_one(
            {'username': {'$regex': f'^{username}$', '$options': 'i'}},
            {'$set': {'lastLogin': datetime.utcnow(), 'updatedAt': datetime.utcnow()}}
        )

def set_user_otp(username):
    """Generates and sets an OTP for a user."""
    mongo_db = get_db()
    if mongo_db is None:
        return None

    # Generate a 6-digit OTP
    otp = "".join(random.choices(string.digits, k=6))
    otp_expiration = datetime.utcnow() + timedelta(minutes=10) # OTP expires in 10 minutes

    try:
        mongo_db.users.update_one(
            {'username': {'$regex': f'^{username}$', '$options': 'i'}},
            {'$set': {
                'otp': otp,
                'otpExpiresAt': otp_expiration,
                'updatedAt': datetime.utcnow()
            }}
        )
        print(f"Generated OTP {otp} for user {username}")
        # In a real app, you would add your email sending logic here
        return otp # Return OTP for testing purposes
    except Exception as e:
        print(f"Error setting OTP for user {username}: {e}")
        return None

def verify_user_otp(username, submitted_otp):
    """Verifies the user's OTP and activates the account."""
    mongo_db = get_db()
    if mongo_db is None:
        return False

    user = get_user_by_username(username)
    if not user:
        return False

    # Check if OTP matches and is not expired
    if user.get('otp') == submitted_otp and user.get('otpExpiresAt') > datetime.utcnow():
        # OTP is correct, activate user and clear OTP fields
        mongo_db.users.update_one(
            {'username': {'$regex': f'^{username}$', '$options': 'i'}},
            {'$set': {
                'isActive': True,
                'updatedAt': datetime.utcnow()
            },
            '$unset': {
                'otp': "",
                'otpExpiresAt': ""
            }}
        )
        print(f"User {username} successfully verified.")
        return True
    
    print(f"OTP verification failed for user {username}.")
    return False