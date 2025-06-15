# website/models.py

# Dummy user data stored in a dictionary (in-memory).
# In a real application, this would be a database (e.g., SQLAlchemy model).
# Passwords here are plain text for demonstration - NEVER DO THIS IN PRODUCTION!
# Use password hashing (e.g., Werkzeug.security.generate_password_hash)
users = {
    'admin': {
        'password': 'admin', # Insecure! Use hashed passwords!
        'email': 'admin@example.com'
    }
}

def get_user_by_username(username):
    """Retrieves user data by username."""
    # Returns the user dictionary or None if not found
    return users.get(username)

def add_user(username, email, password):
    """Adds a new user to the dummy storage."""
    if username in users:
        return False # User already exists

    # Add the new user (store hashed password in production!)
    users[username] = {'password': password, 'email': email}
    return True # User added successfully