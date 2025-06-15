from flask import Blueprint, render_template, request, redirect, url_for, session, flash

# Define the blueprint. The name 'main' is used when calling url_for('main.endpoint_name').
main = Blueprint('main', __name__)

# Define available branch categories as specific locations
# In a real app, this might come from a database
BRANCH_CATEGORIES = [
    {'name': 'DOUBLE L', 'icon': 'building_icon.png'}, # Example icon name
    {'name':  'SUB-URBAN', 'icon': 'building_icon.png'}, # <-- Added comma here
    {'name': 'KASIGLAHAN', 'icon': 'building_icon.png'}, # <-- Added comma here
    {'name': 'SOUTHVILLE 8B', 'icon': 'building_icon.png'}, # <-- Added comma here
    {'name': 'SITIO TANAG', 'icon': 'building_icon.png'} # No comma needed after the last item
    # Add more specific branch names/addresses as needed
]


# Route for the Branches page
@main.route('/branches')
def branches():
    """Displays the branches selection page after successful login."""
    # This page requires login
    if 'username' in session:
         username = session['username'] # Get username if needed for the template
         # Pass the list of branches to the template
         return render_template('branches.html', username=username, branches=BRANCH_CATEGORIES)
    else:
         # If not logged in, redirect to login page
        flash('You need to be logged in to see this page.', 'error')
        return redirect(url_for('auth.login'))


# Route to handle selecting a branch
@main.route('/select_branch/<branch_name>')
def select_branch(branch_name):
    """Handles branch selection and redirects to the dashboard."""
    if 'username' in session:
        # Optional: Store selected branch name in session
        session['selected_branch'] = branch_name
        flash(f'Branch "{branch_name}" selected.', 'info') # Optional feedback
        # Redirect to the dashboard
        return redirect(url_for('main.dashboard'))
    else:
        # If not logged in, redirect to login page
        flash('You need to be logged in to select a branch.', 'error')
        return redirect(url_for('auth.login'))


# The dashboard route requires login
@main.route('/dashboard')
def dashboard():
    """Displays the dashboard if the user is logged in."""
    # Check if the user is in the session (i.e., if they are logged in)
    if 'username' in session:
        username = session['username']
        # Optional: Get selected branch from session to display on dashboard
        selected_branch = session.get('selected_branch', 'No specific branch selected')
        # Pass username and selected_branch to template
        return render_template('dashboard.html', username=username, selected_branch=selected_branch)
    else:
        # If not logged in, flash message and redirect to login page
        flash('You need to be logged in to see this page.', 'error')
        # Redirect to the login endpoint in the 'auth' blueprint
        return redirect(url_for('auth.login'))
