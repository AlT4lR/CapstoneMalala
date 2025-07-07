# website/auth.py

from flask import Blueprint, render_template, request, redirect, url_for, session, flash
# Import the new, corrected model functions
from .models import get_user_by_username, add_user, check_password, update_last_login
import re

auth = Blueprint('auth', __name__)

@auth.route('/login', methods=['GET'])
def login():
    if 'username' in session:
        return redirect(url_for('main.branches'))
    return render_template('login.html')

# Renamed this function for clarity
@auth.route('/login', methods=['POST'])
def login_post():
    username = request.form.get('username')
    password = request.form.get('password')

    user = get_user_by_username(username)

    # Use the new check_password function
    if user and check_password(user['passwordHash'], password):
        session['username'] = user['username']
        update_last_login(user['username']) # Update last login time
        flash('Login successful!', 'success')
        return redirect(url_for('main.branches'))
    else:
        flash('Invalid username or password', 'error')
        return redirect(url_for('auth.login'))

@auth.route('/register', methods=['GET'])
def register():
    return render_template('register.html')

# Renamed this function for clarity
@auth.route('/register', methods=['POST'])
def register_post():
    username = request.form.get('username')
    email = request.form.get('email')
    password = request.form.get('password')

    # --- Server-Side Validation ---
    if not all([username, email, password]):
        flash('All fields are required.', 'error')
        return render_template('register.html', username=username, email=email)
        
    if len(password) < 8:
        flash('Password must be at least 8 characters long.', 'error')
        return render_template('register.html', username=username, email=email)
        
    if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
        flash('Invalid email address.', 'error')
        return render_template('register.html', username=username)

    # Use the new add_user function
    if add_user(username, email, password):
        flash('Registration successful! Please log in.', 'success')
        return redirect(url_for('auth.login'))
    else:
        # This now correctly catches if the username or email is already taken
        flash('Username or Email already exists. Please choose another.', 'error')
        return render_template('register.html', username=username, email=email)


@auth.route('/logout')
def logout():
    session.pop('username', None)
    flash('You have been logged out.', 'success')
    return redirect(url_for('auth.login'))