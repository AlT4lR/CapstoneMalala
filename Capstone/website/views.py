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

# Dummy Transaction Data (keep existing)
dummy_transactions = {
    # ... (your existing dummy_transactions) ...
     'trans_12345': {
        'id': '#12345',
        'recipient': 'Jody Sta. Maria',
        'type': 'Payment',
        'date': '05/30/2025',
        'time': '10:00 AM',
        'amount': 999.00,
        'payment_method': 'Bank-to-Bank',
        'notes': 'Payment for services rendered.'
    },
     'trans_3574e5490': {
        'id': 'RQS-3574e5490',
        'recipient': 'Janella Herrera',
        'type': 'Refund',
        'date': '12 Jun',
        'time': '11:42 AM',
        'amount': 500.00,
        'payment_method': 'Online Transfer',
        'notes': 'Refund for returned item.'
    }
}

# Dummy Notification Data (Replace with real data source)
dummy_inbox_notifications = [
    {
        'id': 1,
        'name': 'Security Bank',
        'preview': 'Bill for the week Dear valued customerh', # Typo from image included
        'date': '30 May 2025, 2:00 PM',
        'icon': 'security_bank_icon.png' # Assuming you have this icon in static/images
    },
     {
        'id': 2,
        'name': 'Security Bank',
        'preview': 'Your statement is ready...',
        'date': '30 May 2025, 3:00 PM',
        'icon': 'security_bank_icon.png'
    },
      {
        'id': 3,
        'name': 'Security Bank',
        'preview': 'Upcoming payment reminder...',
        'date': '30 May 2025, 7:00 PM',
        'icon': 'security_bank_icon.png'
    },
       {
        'id': 4,
        'name': 'Security Bank',
        'preview': 'Security alert: new login detected...',
        'date': '30 May 2025, 9:00 PM',
        'icon': 'security_bank_icon.png'
    }
    # Add more inbox notifications
]

dummy_archive_notifications = [
     {
        'id': 5,
        'name': 'Security Bank',
        # 'preview': 'Payment received confirmation...', # Archive might not show preview in this layout
        'date': '30 June 2025, 9:00 AM',
        'icon': 'security_bank_icon.png'
    }
    # Add more archive notifications
]


# Route for the Branches page (keep existing)
@main.route('/branches')
def branches():
    """Displays the branches selection page after successful login."""
    if 'username' in session:
         username = session['username']
         return render_template('branches.html', username=username, branches=BRANCH_CATEGORIES)
    else:
        flash('You need to be logged in to see this page.', 'error')
        return redirect(url_for('auth.login'))


# Route to handle selecting a branch (keep existing)
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

# The dashboard route requires login (keep existing)
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

# Route for the transactions page (keep existing)
@main.route('/transactions')
def transactions():
    """Displays the transactions page if the user is logged in."""
    if 'username' in session:
        username = session['username']
        selected_branch = session.get('selected_branch', 'No specific branch selected')
        # Pass dummy transactions (using values() to get the list of transaction dicts)
        return render_template('transactions.html', username=username, selected_branch=selected_branch, transactions=dummy_transactions.values())
    else:
        flash('You need to be logged in to see this page.', 'error')
        return redirect(url_for('auth.login'))

# Route for displaying transaction details (keep existing)
@main.route('/transactions/<transaction_id>')
def transaction_details(transaction_id):
    """Displays the details of a specific transaction."""
    if 'username' in session:
        username = session['username']
        selected_branch = session.get('selected_branch', 'No specific branch selected')
        transaction = dummy_transactions.get(transaction_id)
        if transaction:
            return render_template('transaction_details.html',
                                   username=username,
                                   selected_branch=selected_branch,
                                   transaction=transaction)
        else:
            flash('Transaction not found.', 'error')
            return redirect(url_for('main.transactions'))
    else:
        flash('You need to be logged in to see this page.', 'error')
        return redirect(url_for('auth.login'))

# New route for the notifications page
@main.route('/notifications')
def notifications():
    """Displays the notifications page if the user is logged in."""
    if 'username' in session:
        username = session['username']
        selected_branch = session.get('selected_branch', 'No specific branch selected')
        # Pass dummy notification data
        return render_template('notifications.html',
                               username=username,
                               selected_branch=selected_branch,
                               inbox_notifications=dummy_inbox_notifications,
                               archive_notifications=dummy_archive_notifications) # Pass both lists
    else:
        flash('You need to be logged in to see this page.', 'error')
        return redirect(url_for('auth.login'))