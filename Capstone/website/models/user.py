import bcrypt
import logging
from datetime import datetime, timedelta
import pytz
import pyotp
import re
import random
import string
from pymongo.errors import DuplicateKeyError
from flask import current_app
from ..constants import LOGIN_ATTEMPT_LIMIT, LOCKOUT_DURATION_MINUTES

logger = logging.getLogger(__name__)

def get_user_by_username(username):
    db = current_app.db
    if db is None: return None
    # Use case-insensitive regex search for fetching
    return db.users.find_one({'username': {'$regex': f'^{re.escape(username.strip().lower())}$', '$options': 'i'}})

def get_user_by_email(email):
    db = current_app.db
    if db is None: return None
    # Use case-insensitive regex search for fetching
    return db.users.find_one({'email': {'$regex': f'^{re.escape(email.strip().lower())}$', '$options': 'i'}})

def add_user(username, email, password, name):
    """
    Adds a new user to the database with all default fields, including
    name and an initial empty profile picture URL.
    """
    db = current_app.db
    if db is None: return False
    hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
    otp_secret = pyotp.random_base32()
    try:
        db.users.insert_one({
            'username': username.strip().lower(),
            'name': name.strip(),
            'email': email.strip().lower(),
            'passwordHash': hashed_password,
            'profile_picture_url': None,  # Added support for profile picture storage
            'isActive': False,
            'otpSecret': otp_secret,
            'createdAt': datetime.now(pytz.utc),
            'failedLoginAttempts': 0,
            'lockoutUntil': None,
            'lastLogin': None,
            'notes': '',
            'push_subscriptions': []
        })
        return True
    except DuplicateKeyError:
        return False

def check_password(stored_hash, provided_password):
    """Verifies the provided password against the stored hash."""
    try:
        return bcrypt.checkpw(provided_password.encode('utf-8'), stored_hash)
    except (TypeError, ValueError):
        return False

def update_last_login(username):
    """Resets failed attempts and updates the last login timestamp."""
    db = current_app.db
    if db is None: return
    db.users.update_one(
        {'username': {'$regex': f'^{re.escape(username.strip().lower())}$', '$options': 'i'}},
        {'$set': {'lastLogin': datetime.now(pytz.utc), 'failedLoginAttempts': 0, 'lockoutUntil': None}}
    )

def record_failed_login_attempt(username):
    """Increments failed login attempts and applies lockout if the limit is reached."""
    db = current_app.db
    if db is None: return
    user = get_user_by_username(username)
    if not user: return
    new_attempts = user.get('failedLoginAttempts', 0) + 1
    update_fields = {'$set': {'failedLoginAttempts': new_attempts}}
    if new_attempts >= LOGIN_ATTEMPT_LIMIT:
        lockout_time = datetime.now(pytz.utc) + timedelta(minutes=LOCKOUT_DURATION_MINUTES)
        update_fields['$set']['lockoutUntil'] = lockout_time
    db.users.update_one({'_id': user['_id']}, update_fields)

def update_user_password(username, new_password):
    """Updates a user's password hash."""
    db = current_app.db
    if db is None: return False
    hashed_password = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt())
    result = db.users.update_one(
        {'username': {'$regex': f'^{re.escape(username.strip().lower())}$', '$options': 'i'}},
        {'$set': {'passwordHash': hashed_password}}
    )
    return result.matched_count == 1

def set_user_otp(username, otp_type='email'):
    """Generates and sets a 6-digit OTP for email verification."""
    db = current_app.db
    if db is None: return None
    user = get_user_by_username(username)
    if not user: return None
    if otp_type == 'email':
        otp = "".join(random.choices(string.digits, k=6))
        db.users.update_one({'_id': user['_id']}, {'$set': {'otp': otp, 'otpExpiresAt': datetime.now(pytz.utc) + timedelta(minutes=10)}})
        return otp
    return None

def verify_user_otp(username, submitted_otp, otp_type='email'):
    """Verifies the submitted OTP against the stored one (email) or the TOTP secret (2FA)."""
    db = current_app.db
    if db is None: return False
    user = get_user_by_username(username)
    if not user: return False
    if otp_type == 'email':
        if user.get('otp') == submitted_otp and user.get('otpExpiresAt', datetime.min.replace(tzinfo=pytz.utc)) > datetime.now(pytz.utc):
            # Also set isActive to True upon successful email verification
            db.users.update_one({'_id': user['_id']}, {'$set': {'isActive': True}, '$unset': {'otp': "", 'otpExpiresAt': ""}})
            return True
    elif otp_type == '2fa':
        totp = pyotp.TOTP(user['otpSecret'])
        return totp.verify(submitted_otp, valid_window=1)
    return False

def save_push_subscription(username, subscription_info):
    """Saves a VAPID push subscription for a user."""
    db = current_app.db
    if db is None: return False
    try:
        # Use lowercased username for consistency
        db.users.update_one({'username': username.lower()}, {'$addToSet': {'push_subscriptions': subscription_info}})
        return True
    except Exception as e:
        logger.error(f"Error saving push subscription for {username}: {e}", exc_info=True)
        return False

def get_user_push_subscriptions(username):
    """Retrieves all push subscriptions for a user."""
    db = current_app.db
    if db is None: return []
    user = get_user_by_username(username)
    return user.get('push_subscriptions', []) if user else []

def update_personal_info(username, new_data):
    """
    Updates the user's name and/or profile picture URL.
    This includes the necessary logic to handle the `profile_picture_url` field.
    """
    db = current_app.db
    if db is None: return False
    try:
        update_doc = {'$set': {}}
        
        if 'name' in new_data and new_data['name']:
            update_doc['$set']['name'] = new_data['name']
        
        # Logic to update profile picture URL, crucial for the sidebar feature
        if 'profile_picture_url' in new_data:
            # Note: new_data['profile_picture_url'] can be None to clear the picture
            update_doc['$set']['profile_picture_url'] = new_data['profile_picture_url']
            
        if not update_doc['$set']:
            return True # Nothing to update

        result = db.users.update_one({'username': username.lower()}, update_doc)
        
        # Return True if a document was matched, even if no fields were technically changed.
        return result.matched_count > 0
        
    except Exception as e:
        logger.error(f"Error updating personal info for {username}: {e}", exc_info=True)
        return False