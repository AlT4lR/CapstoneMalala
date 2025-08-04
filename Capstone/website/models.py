# website/models.py

from flask import current_app
import pytz
from . import get_db # Will now access db via current_app.db
import bcrypt
from pymongo.errors import DuplicateKeyError, OperationFailure
import logging
from datetime import datetime, timedelta
import random
import string
import pyotp

logger = logging.getLogger(__name__)

# --- User Operations ---
def get_user_by_username(username):
    """Retrieves a user document from MongoDB by username (case-insensitive)."""
    db = current_app.db # Access db via current_app
    if not db:
        logger.error("Database not available.")
        return None
    
    # Use case-insensitive regex for lookup, matching the index's behavior
    return db.users.find_one({'username': {'$regex': f'^{username}$', '$options': 'i'}})

def add_user(username, email, password):
    """
    Adds a new user to MongoDB with isActive set to False.
    Returns True on success, False on failure.
    Handles case-insensitivity for username and email during insertion attempt.
    """
    db = current_app.db
    if not db:
        logger.error("Database not available.")
        return False

    hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
    otp_secret = pyotp.random_base32() # Generate PyOTP secret for 2FA
    
    user_data = {
        'username': username.strip(), # Clean whitespace
        'email': email.strip().lower(), # Normalize email to lowercase
        'passwordHash': hashed_password,
        'role': 'user',
        'isActive': False,
        'otp': None, 
        'otpExpiresAt': None,
        'otpSecret': otp_secret,
        'failedLoginAttempts': 0,
        'lockoutUntil': None,
        'lastLogin': None,
        'createdAt': datetime.utcnow(),
        'updatedAt': datetime.utcnow()
    }

    try:
        # Use the cleaned/normalized username and email for insertion
        result = db.users.insert_one(user_data)
        logger.info(f"Successfully registered user: {user_data['username']} (ID: {result.inserted_id}). Awaiting verification.")
        return True
    except DuplicateKeyError:
        # Check which field caused the duplicate key error
        # This requires inspecting the exception or doing separate checks first if needed
        # For simplicity, we'll give a general message
        logger.warning(f"Registration failed: Username '{username}' or Email '{email}' already exists.")
        return False
    except OperationFailure as e: # Catch potential issues with index enforcement if it wasn't case-insensitive
        logger.error(f"MongoDB operation failed during user registration for {username}: {e}")
        return False
    except Exception as e:
        logger.error(f"An unexpected error occurred during user registration for {username}: {e}")
        return False

def check_password(stored_hash, provided_password):
    """Checks a provided password against a stored bcrypt hash."""
    try:
        return bcrypt.checkpw(provided_password.encode('utf-8'), stored_hash)
    except (TypeError, ValueError): # Handle potential errors with hash format
        logger.error("Invalid password hash format encountered.")
        return False

def update_last_login(username):
    """Updates the lastLogin timestamp for a user and resets failed login attempts and lockout."""
    db = current_app.db
    if not db:
        logger.error("Database not available.")
        return

    try:
        result = db.users.update_one(
            {'username': {'$regex': f'^{username}$', '$options': 'i'}}, # Case-insensitive lookup
            {'$set': {
                'lastLogin': datetime.utcnow(),
                'failedLoginAttempts': 0,
                'lockoutUntil': None,
                'updatedAt': datetime.utcnow()
            }}
        )
        if result.modified_count == 0:
            logger.warning(f"update_last_login: No user found or updated for username: {username}")
    except Exception as e:
        logger.error(f"Error updating last login for {username}: {e}")

def record_failed_login_attempt(username):
    """Increments failed login attempts and applies lockout if threshold is met."""
    db = current_app.db
    if not db:
        logger.error("Database not available.")
        return

    LOCKOUT_THRESHOLD = 5
    LOCKOUT_DURATION_MINUTES = 10

    # Find user first to check current state and attempts
    user = get_user_by_username(username)
    if not user:
        logger.warning(f"record_failed_login_attempt: User '{username}' not found.")
        return # User not found, nothing to update

    new_attempts = user.get('failedLoginAttempts', 0) + 1
    update_fields = {'failedLoginAttempts': new_attempts, 'updatedAt': datetime.utcnow()}

    if new_attempts >= LOCKOUT_THRESHOLD and not user.get('lockoutUntil'): # Apply lockout only if not already locked
        lockout_time = datetime.utcnow() + timedelta(minutes=LOCKOUT_DURATION_MINUTES)
        update_fields['lockoutUntil'] = lockout_time
        logger.warning(f"User '{username}' locked out until {lockout_time} due to {new_attempts} failed attempts.")
    
    try:
        db.users.update_one(
            {'username': user['username']}, # Use exact username for update consistency
            {'$set': update_fields}
        )
    except Exception as e:
        logger.error(f"Error recording failed login attempt for {username}: {e}")

def set_user_otp(username, otp_type='email'):
    """
    Generates and sets an OTP for a user.
    otp_type='email': Generates numeric OTP for email verification.
    otp_type='2fa': (Conceptual) Ensures a PyOTP secret exists. Secret is generated in add_user.
    Returns the generated OTP or secret if applicable, None on failure.
    """
    db = current_app.db
    if not db:
        logger.error("Database not available.")
        return None

    user = get_user_by_username(username)
    if not user:
        logger.warning(f"set_user_otp: User '{username}' not found.")
        return None

    if otp_type == 'email':
        otp = "".join(random.choices(string.digits, k=6))
        otp_expiration = datetime.utcnow() + timedelta(minutes=10)

        try:
            result = db.users.update_one(
                {'username': user['username']},
                {'$set': {
                    'otp': otp,
                    'otpExpiresAt': otp_expiration,
                    'updatedAt': datetime.utcnow()
                }}
            )
            if result.modified_count > 0:
                logger.info(f"Generated email OTP for user '{username}'.")
                return otp
            else:
                logger.warning(f"set_user_otp: No user updated for email OTP generation for '{username}'.")
                return None
        except Exception as e:
            logger.error(f"Error setting email OTP for user {username}: {e}")
            return None
            
    elif otp_type == '2fa':
        # This function is primarily for ensuring the secret exists.
        # The secret is generated during add_user. If it's missing later, it can be regenerated.
        if not user.get('otpSecret'):
            new_secret = pyotp.random_base32()
            try:
                result = db.users.update_one(
                    {'username': user['username']},
                    {'$set': {'otpSecret': new_secret, 'updatedAt': datetime.utcnow()}}
                )
                if result.modified_count > 0:
                    logger.info(f"Generated new 2FA secret for user '{username}'.")
                    return new_secret
                else:
                    logger.warning(f"set_user_otp: No user updated for 2FA secret generation for '{username}'.")
                    return None
            except Exception as e:
                logger.error(f"Error generating 2FA secret for {username}: {e}")
                return None
        else:
            # Secret already exists, return it
            return user.get('otpSecret')
            
    return None

def verify_user_otp(username, submitted_otp, otp_type='email'):
    """
    Verifies the user's OTP.
    otp_type='email': Verifies against stored email OTP and activates account.
    otp_type='2fa': Verifies against PyOTP secret for login.
    Returns True if verification is successful, False otherwise.
    """
    db = current_app.db
    if not db:
        logger.error("Database not available.")
        return False

    user = get_user_by_username(username)
    if not user:
        logger.warning(f"verify_user_otp: User '{username}' not found.")
        return False

    if otp_type == 'email':
        if user.get('otp') == submitted_otp and user.get('otpExpiresAt') and user.get('otpExpiresAt') > datetime.utcnow():
            try:
                result = db.users.update_one(
                    {'username': user['username']},
                    {'$set': {'isActive': True, 'updatedAt': datetime.utcnow()},
                     '$unset': {'otp': "", 'otpExpiresAt': ""}} # Clear OTP fields
                )
                if result.modified_count > 0:
                    logger.info(f"User '{username}' successfully verified via email OTP and activated.")
                    return True
                else:
                    logger.warning(f"verify_user_otp: User '{username}' email OTP verified, but no user document was modified.")
                    return True # Still consider it a success if verification logic passed
            except Exception as e:
                logger.error(f"Error activating user '{username}' after email OTP verification: {e}")
                return False # Activation failed
        else:
            logger.info(f"Email OTP verification failed for user '{username}': Invalid or expired OTP.")
            return False
            
    elif otp_type == '2fa':
        otp_secret = user.get('otpSecret')
        if not otp_secret:
            logger.warning(f"verify_user_otp: No 2FA secret found for user '{username}' during verification.")
            return False

        totp = pyotp.TOTP(otp_secret)
        if totp.verify(submitted_otp, valid_window=1): # Allow +/- 1 interval for clock drift
            logger.info(f"User '{username}' successfully verified via 2FA TOTP.")
            return True
        else:
            logger.info(f"2FA TOTP verification failed for user '{username}'.")
            return False
    
    return False

# --- Schedule Operations ---
def add_schedule(username, title, start_time, end_time, category, notes=None):
    """
    Adds a new schedule entry for a user.
    start_time and end_time should be timezone-aware datetime objects (UTC recommended).
    """
    db = current_app.db
    if not db:
        logger.error("Database not available.")
        return False

    if not isinstance(start_time, datetime) or not isinstance(end_time, datetime):
        logger.error("start_time and end_time must be datetime objects.")
        return False
        
    # Ensure times are timezone-aware (default to UTC if naive)
    if start_time.tzinfo is None:
        start_time = start_time.replace(tzinfo=pytz.utc) # Requires pytz for timezone handling
    if end_time.tzinfo is None:
        end_time = end_time.replace(tzinfo=pytz.utc)

    schedule_data = {
        'username': username,
        'title': title.strip(),
        'start_time': start_time,
        'end_time': end_time,
        'category': category.strip(),
        'notes': notes.strip() if notes else None,
        'createdAt': datetime.utcnow(),
        'updatedAt': datetime.utcnow()
    }
    try:
        result = db.schedules.insert_one(schedule_data)
        logger.info(f"Schedule added: {result.inserted_id} for user '{username}' ({title}).")
        return True
    except Exception as e:
        logger.error(f"Error adding schedule for user {username}: {e}")
        return False

def get_schedules_by_date_range(username, start_date, end_date):
    """
    Retrieves schedules for a user within a date range (inclusive).
    start_date and end_date must be timezone-aware datetime objects (UTC).
    """
    db = current_app.db
    if not db:
        logger.error("Database not available.")
        return []

    if not isinstance(start_date, datetime) or not isinstance(end_date, datetime):
        logger.error("start_date and end_date must be datetime objects.")
        return []

    # Ensure inputs are timezone-aware (UTC) for query consistency
    if start_date.tzinfo is None: start_date = start_date.replace(tzinfo=pytz.utc)
    if end_date.tzinfo is None: end_date = end_date.replace(tzinfo=pytz.utc)

    # Adjust end_date to cover the entire last day if it's naive or just a date
    # Query will be: start_time >= start_date AND start_time <= end_date
    # If end_date is just a date, we might want to ensure it covers up to 23:59:59.999999
    # However, using '<' with the next day's start is often cleaner for date ranges.
    # For simplicity, we'll assume the input `end_date` already represents the full range's end.
    # If `end_date` is meant to include the whole day, one might use:
    # end_date_inclusive = end_date.replace(hour=23, minute=59, second=59, microsecond=999999)

    query = {
        'username': username,
        'start_time': {
            '$gte': start_date,
            '$lte': end_date # Adjust if end_date needs to represent the entire day
        }
    }
    
    schedules = []
    try:
        # Find schedules and sort by start_time chronologically
        for doc in db.schedules.find(query).sort('start_time', 1):
            # Convert ObjectId to string for JSON serialization/consistency
            doc['_id'] = str(doc['_id']) 
            # Ensure datetime fields are serializable or formatted as needed
            doc['start_time'] = doc['start_time'].isoformat() if isinstance(doc['start_time'], datetime) else doc['start_time']
            doc['end_time'] = doc['end_time'].isoformat() if isinstance(doc['end_time'], datetime) else doc['end_time']
            schedules.append(doc)
        logger.info(f"Retrieved {len(schedules)} schedules for '{username}' between {start_date} and {end_date}.")
    except OperationFailure as e:
        logger.error(f"MongoDB operation error fetching schedules for {username}: {e}")
    except Exception as e:
        logger.error(f"An unexpected error occurred fetching schedules for {username}: {e}")
    return schedules

# --- Category Operations ---
def get_all_categories(username):
    """
    Retrieves all unique categories for a user from their schedules.
    Returns a default list if no categories are found or DB is unavailable.
    """
    db = current_app.db
    if not db:
        logger.error("Database not available.")
        return ['Office', 'Meetings', 'Events', 'Personal', 'Others'] # Default categories

    # Define default categories to return if none are found or in case of error
    DEFAULT_CATEGORIES = ['Office', 'Meetings', 'Events', 'Personal', 'Others']

    try:
        # Aggregate to find distinct categories for the user
        categories = db.schedules.distinct('category', {'username': username})
        
        # If no categories are found in schedules, return defaults
        if not categories:
            logger.info(f"No categories found in schedules for user '{username}'. Returning defaults.")
            return DEFAULT_CATEGORIES
        
        # Optionally, add user-defined categories if they are stored elsewhere (e.g., user profile)
        # For now, just return categories found in schedules.
        return categories
        
    except Exception as e:
        logger.error(f"Error fetching categories for user '{username}': {e}")
        return DEFAULT_CATEGORIES # Return defaults on error

def add_category(username, category_name):
    """
    Adds a new category. This is a conceptual function for now.
    In a real application, categories might be stored in a separate collection
    or as an array within the user document.
    This function currently just logs the action.
    """
    logger.info(f"Conceptual: Category '{category_name}' added for user '{username}'.")
    # TODO: Implement persistent storage for user-defined categories if needed.
    # For now, returning True to simulate success.
    return True