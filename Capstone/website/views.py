# website/views.py

from flask import Blueprint, render_template, request, redirect, url_for, session, flash

# Define the blueprint.
main = Blueprint('main', __name__)

# Define available branch categories
BRANCH_CATEGORIES = [
    {'name': 'DOUBLE L', 'icon': 'building_icon.png'},
    {'name':  'SUB-URBAN', 'icon': 'building_icon.png'},
    {'name': 'KASIGLAHAN', 'icon': 'building_icon.png'},
    {'name': 'SOUTHVILLE 8B', 'icon': 'building_icon.png'},
    {'name': 'SITIO TANAG', 'icon': 'building_icon.png'}
]

# Dummy Transaction Data (Replace with database query in a real app)
# Using a dictionary for easy lookup by ID
# PLACED AT THE TOP LEVEL TO BE ACCESSIBLE BY ALL ROUTES
dummy_transactions = {
    '#12345': { # Changed key to match the 'id' value
        'id': '#12345',
        'recipient': 'Jody Sta. Maria',
        'type': 'Payment',
        'date': '05/30/2025',
        'time': '10:00 AM',
        'amount': 999.00,
        'payment_method': 'Bank-to-Bank',
        'notes': 'Payment for services rendered.'
    },
     'RQS-3574e5490': { # Changed key to match the 'id' value
        'id': 'RQS-3574e5490',
        'recipient': 'Janella Herrera',
        'type': 'Refund',
        'date': '12 Jun',
        'time': '11:42 AM',
        'amount': 500.00,
        'payment_method': 'Online Transfer',
        'notes': 'Refund for returned item.'
    }
    # Add more dummy transactions with keys matching their 'id' values
}


# Route for the Branches page
@main.route('/branches')
def branches():
    """Displays the branches selection page after successful login."""
    if 'username' in session:
         username = session['username']
         return render_template('branches.html', username=username, branches=BRANCH_CATEGORIES)
    else:
        flash('You need to be logged in to see this page.', 'error')
        return redirect(url_for('auth.login'))


# Route to handle selecting a branch
@main.route('/select_branch/<branch_name>')
def select_branch(branch_name):
    """Handles branch selection and redirects to the dashboard."""
    if 'username' in session:
        session['selected_branch'] = branch_name
        flash(f'Branch "{branch_name}" selected.', 'info')
        return redirect(url_for('main.dashboard'))
    else:
        flash('You need to be logged in to select a branch.', 'error')
        return redirect(url_for('auth.login'))

# The dashboard route requires login
@main.route('/dashboard')
def dashboard():
    """Displays the dashboard if the user is logged in."""
    if 'username' in session:
        username = session['username']
        selected_branch = session.get('selected_branch', 'No specific branch selected')
        return render_template('dashboard.html', username=username, selected_branch=selected_branch)
    else:
        flash('You need to be logged in to see this page.', 'error')
        return redirect(url_for('auth.login'))

# Route for the transactions page
@main.route('/transactions')
def transactions():
    """Displays the transactions page if the user is logged in."""
    if 'username' in session:
        username = session['username']
        selected_branch = session.get('selected_branch', 'No specific branch selected')
        # In a real app, filter transactions by the selected branch
        # For now, we'll pass all dummy transactions
        return render_template('transactions.html', username=username, selected_branch=selected_branch, transactions=dummy_transactions.values())
    else:
        flash('You need to be logged in to see this page.', 'error')
        return redirect(url_for('auth.login'))

# New route for displaying transaction details
@main.route('/transactions/<transaction_id>')
def transaction_details(transaction_id):
    """Displays the details of a specific transaction."""
    if 'username' in session:
        username = session['username']
        selected_branch = session.get('selected_branch', 'No specific branch selected')

        # Retrieve the transaction details using the ID (now using the correct keys)
        # In a real app, this would be a database query
        transaction = dummy_transactions.get(transaction_id)

        if transaction:
            return render_template('transaction_details.html',
                                   username=username,
                                   selected_branch=selected_branch,
                                   transaction=transaction)
        else:
            # Handle case where transaction is not found
            flash('Transaction not found.', 'error')
            return redirect(url_for('main.transactions')) # Redirect back to the list
    else:
        flash('You need to be logged in to see this page.', 'error')
        return redirect(url_for('auth.login'))