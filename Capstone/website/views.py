from flask import Blueprint, render_template, request, redirect, url_for, session, flash

# Define the blueprint. The name 'main' is used when calling url_for('main.endpoint_name').
main = Blueprint('main', __name__)

# The dashboard route requires login
@main.route('/dashboard')
def dashboard():
    """Displays the dashboard if the user is logged in."""
    # Check if the user is in the session (i.e., if they are logged in)
    if 'username' in session:
        username = session['username']
        # Render the new dashboard template and pass the username
        return render_template('dashboard.html', username=username)
    else:
        # If not logged in, flash message and redirect to login page
        flash('You need to be logged in to see this page.', 'error')
        # Redirect to the login endpoint in the 'auth' blueprint
        return redirect(url_for('auth.login'))

# You could add other main routes here that might also require login, etc.
# For example, a profile page:
# @main.route('/profile')
# def profile():
#     if 'username' in session:
#         # Logic to show profile
#         return "User Profile Page (protected)"
#     else:
#         flash('You need to be logged in to see this page.', 'error')
#         return redirect(url_for('auth.login'))