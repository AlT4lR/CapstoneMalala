# website/auth.py

from flask import Blueprint, render_template, request, redirect, url_for, session, flash
# Import the dummy user data and functions from our models file
from .models import users, add_user, get_user_by_username
# Import the create_app function (needed for password hashing if you implement it here)
# from . import create_app # Uncomment if needed

# Import password hashing utilities (if you've installed Werkzeug)
# from werkzeug.security import generate_password_hash, check_password_hash

# Define the blueprint. The name 'auth' is used when calling url_for('auth.endpoint_name').
auth = Blueprint('auth', __name__)

# Route for the login page (handles both GET requests and the root path)
@auth.route('/login', methods=['GET'])
@auth.route('/', methods=['GET']) # Also handle the root URL
def login():
    """Displays the login page or redirects to branches if logged in."""
    # If user is already logged in, redirect to the branches page
    if 'username' in session:
        # Redirect to the 'branches' endpoint in the 'main' blueprint
        return redirect(url_for('main.branches'))
    # Otherwise, show the login page
    return render_template('login.html')

# Route for handling login form submission
@auth.route('/auth', methods=['POST']) # Form action points here
def auth_post():
    """Handles the login form submission."""
    username = request.form.get('username') # Use .get() to avoid KeyError if field is missing
    password = request.form.get('password')

    user_data = get_user_by_username(username)

    # Check if user exists and password is correct (compare hashed passwords in production!)
    # In production: if user_data and check_password_hash(user_data['password_hash'], password):
    if user_data and user_data['password'] == password:
        # Login successful: Store username in session
        session['username'] = username
        # Redirect to the branches endpoint in the 'main' blueprint
        flash('Login successful!', 'success') # Optional: add a success message
        return redirect(url_for('main.branches'))
    else:
        # Login failed: Flash error message
        flash('Invalid username or password', 'error')
        # Redirect back to the login page (using the blueprint endpoint name)
        return redirect(url_for('auth.login'))

# Route for registration page and handling registration form submission
@auth.route('/register', methods=['GET', 'POST'])
def register():
    """Displays the registration page or handles registration form submission."""
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password') # Get password

        # Hash password in production!
        # hashed_password = generate_password_hash(password, method='pbkdf2:sha256')

        # Basic validation and add user (add hashed_password in production)
        if add_user(username, email, password): # Update add_user to accept hashed password
            flash('Registration successful! Please log in.', 'success')
            # Redirect to the login page (using the blueprint endpoint name)
            return redirect(url_for('auth.login'))
        else:
            flash('Username already exists!', 'error')
            # Redirect back to the registration page (using the blueprint endpoint name)
            return redirect(url_for('auth.register'))

    # For a GET request, just show the registration page
    return render_template('register.html')

# Route for logging out
@auth.route('/logout')
def logout():
    """Logs out the current user by clearing the session."""
    session.pop('username', None) # Remove username from session
    flash('You have been logged out.', 'success')
    # Redirect back to the login page (using the blueprint endpoint name)
    return redirect(url_for('auth.login'))