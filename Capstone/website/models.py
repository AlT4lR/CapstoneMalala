# website/models.py

from . import get_db
import bcrypt
from pymongo.errors import DuplicateKeyError
from datetime import datetime, timedelta
import random
import string
import pyotp

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
        
        # Generate a random base32 secret for PyOTP 2FA
        otp_secret = pyotp.random_base32()

        user_data = {
            'username': username,
            'email': email.lower(),
            'passwordHash': hashed_password,
            'role': 'user',
            'isActive': False,  # User is inactive until initial email OTP verification
            'otp': None, # For email OTP
            'otpExpiresAt': None, # For email OTP
            'otpSecret': otp_secret, # For PyOTP 2FA
            'failedLoginAttempts': 0, # Track failed login attempts
            'lockoutUntil': None, # Timestamp for lockout duration
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
    """Updates the lastLogin timestamp for a user and resets failed login attempts."""
    mongo_db = get_db()

    if mongo_db is not None:
        mongo_db.users.update_one(
            {'username': {'$regex': f'^{username}$', '$options': 'i'}},
            {'$set': {
                'lastLogin': datetime.utcnow(),
                'failedLoginAttempts': 0, # Reset failed attempts on successful login
                'lockoutUntil': None, # Clear lockout on successful login
                'updatedAt': datetime.utcnow()
            }}
        )

def record_failed_login_attempt(username):
    """Increments failed login attempts and applies lockout if threshold is met."""
    mongo_db = get_db()
    if mongo_db is None:
        return

    LOCKOUT_THRESHOLD = 5 # Number of failed attempts before lockout
    LOCKOUT_DURATION_MINUTES = 10 # Lockout duration in minutes

    user = get_user_by_username(username)
    if not user:
        return # User not found, no need to track attempts for non-existent users

    new_attempts = user.get('failedLoginAttempts', 0) + 1
    update_fields = {'failedLoginAttempts': new_attempts, 'updatedAt': datetime.utcnow()}

    if new_attempts >= LOCKOUT_THRESHOLD:
        # Calculate lockout time
        lockout_time = datetime.utcnow() + timedelta(minutes=LOCKOUT_DURATION_MINUTES)
        update_fields['lockoutUntil'] = lockout_time
        print(f"User {username} locked out until {lockout_time} due to {new_attempts} failed attempts.")
    
    mongo_db.users.update_one(
        {'username': user['username']}, # Use exact username to avoid regex issues with updates
        {'$set': update_fields}
    )

def set_user_otp(username, otp_type='email'):
    """
    Generates and sets an OTP for a user.
    If otp_type is 'email', generates numeric OTP for email verification.
    If otp_type is '2fa', generates a PyOTP secret if not already set.
    """
    mongo_db = get_db()
    if mongo_db is None:
        return None

    if otp_type == 'email':
        # Generate a 6-digit OTP for email verification
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
            print(f"Generated email OTP {otp} for user {username}")
            return otp
        except Exception as e:
            print(f"Error setting email OTP for user {username}: {e}")
            return None
    elif otp_type == '2fa':
        # This function is primarily for generating the secret during registration.
        # It's not for generating one-time codes.
        # The secret is already generated in add_user.
        # This part might be adjusted if 2FA setup is a separate flow.
        user = get_user_by_username(username)
        if user and not user.get('otpSecret'):
            new_secret = pyotp.random_base32()
            mongo_db.users.update_one(
                {'username': user['username']},
                {'$set': {'otpSecret': new_secret, 'updatedAt': datetime.utcnow()}}
            )
            return new_secret
        return user.get('otpSecret')
    return None

def verify_user_otp(username, submitted_otp, otp_type='email'):
    """
    Verifies the user's OTP and activates the account if email OTP.
    If otp_type is 'email', verifies against stored email OTP.
    If otp_type is '2fa', verifies against PyOTP secret.
    """
    mongo_db = get_db()
    if mongo_db is None:
        return False

    user = get_user_by_username(username)
    if not user:
        return False

    if otp_type == 'email':
        # Check if email OTP matches and is not expired
        if user.get('otp') == submitted_otp and user.get('otpExpiresAt') and user.get('otpExpiresAt') > datetime.utcnow():
            # OTP is correct, activate user and clear OTP fields
            mongo_db.users.update_one(
                {'username': {'$regex': f'^{username}$', '$options': 'i'}},
                {'$set': {
                    'isActive': True,
                    'updatedAt': datetime.utcnow()
                },
                '$unset': { # Clear OTP fields after successful verification
                    'otp': "",
                    'otpExpiresAt': ""
                }}
            )
            print(f"User {username} successfully verified via email OTP.")
            return True
        print(f"Email OTP verification failed for user {username}.")
        return False
    elif otp_type == '2fa':
        otp_secret = user.get('otpSecret')
        if not otp_secret:
            print(f"No 2FA secret found for user {username}.")
            return False

        totp = pyotp.TOTP(otp_secret)
        # MODIFIED: Added valid_window=1 to allow for minor time drift
        if totp.verify(submitted_otp, valid_window=1):
            print(f"User {username} successfully verified via 2FA TOTP.")
            return True
        print(f"2FA TOTP verification failed for user {username}.")
        return False
    
    return False

# ADDED: Schedule Management Functions
def add_schedule(username, title, start_time, end_time, category, notes=None):
    """
    Adds a new schedule entry for a user.
    start_time and end_time should be datetime objects.
    """
    mongo_db = get_db()
    if mongo_db is None:
        return False

    schedule_data = {
        'username': username,
        'title': title,
        'start_time': start_time,
        'end_time': end_time,
        'category': category,
        'notes': notes,
        'createdAt': datetime.utcnow(),
        'updatedAt': datetime.utcnow()
    }
    try:
        result = mongo_db.schedules.insert_one(schedule_data)
        print(f"Schedule added: {result.inserted_id} for user {username}")
        return True
    except Exception as e:
        print(f"Error adding schedule for user {username}: {e}")
        return False

def get_schedules_by_date_range(username, start_date, end_date):
    """
    Retrieves schedules for a given user within a date range.
    start_date and end_date should be datetime objects, representing the inclusive range.
    """
    mongo_db = get_db()
    if mongo_db is None:
        return []

    # Ensure start_date and end_date cover the entire day
    # start_date = datetime(start_date.year, start_date.month, start_date.day, 0, 0, 0)
    # end_date = datetime(end_date.year, end_date.month, end_date.day, 23, 59, 59)

    query = {
        'username': username,
        'start_time': {
            '$gte': start_date,
            '$lte': end_date
        }
    }
    
    schedules = []
    try:
        # Sort by start_time to ensure chronological order
        for doc in mongo_db.schedules.find(query).sort('start_time', 1):
            doc['_id'] = str(doc['_id']) # Convert ObjectId to string for JSON serialization
            schedules.append(doc)
    except Exception as e:
        print(f"Error fetching schedules for user {username}: {e}")
    return schedules

# For categories
def get_all_categories(username):
    """
    Retrieves all unique categories for a user from existing schedules,
    or returns a default set if no schedules exist or a fixed list is preferred.
    """
    mongo_db = get_db()
    if mongo_db is None:
        return ['Office', 'Meetings', 'Events', 'Personal', 'Others'] # Default categories

    try:
        # Aggregate to find distinct categories for the user
        categories = mongo_db.schedules.distinct('category', {'username': username})
        if not categories:
            return ['Office', 'Meetings', 'Events', 'Personal', 'Others'] # Fallback to defaults
        return categories
    except Exception as e:
        print(f"Error fetching categories for user {username}: {e}")
        return ['Office', 'Meetings', 'Events', 'Personal', 'Others'] # Fallback on error

def add_category(username, category_name):
    """
    Adds a new category. For simplicity, we'll store categories as part of user settings
    or just ensure uniqueness when used in schedules.
    For this implementation, it's mostly conceptual unless a dedicated 'categories' collection exists.
    We'll simply ensure it can be used for new schedules.
    """
    # In a real app, you might have a dedicated 'categories' collection
    # or an array of categories within the user document.
    # For now, this function serves as a placeholder to acknowledge the action.
    print(f"Category '{category_name}' added (conceptually) for user {username}.")
    return True