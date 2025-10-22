# create_notifications_task.py
import os
from datetime import datetime, timedelta
import pytz
from website import create_app
from website.models import add_notification
from flask import url_for

app = create_app(os.getenv('FLASK_CONFIG') or 'dev')

def check_due_transactions_and_notify():
    """
    Scans for pending transactions due today and creates notifications for the respective users.
    Handles both legacy transactions (with check_date) and new transactions (with due_date).
    """
    with app.app_context():
        db = app.db
        if db is None:
            print("Error: Database connection not available.")
            return

        # Define today's date range in UTC
        today_start = datetime.now(pytz.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        today_end = today_start + timedelta(days=1)
        
        print(f"Checking for transactions due between {today_start} and {today_end}...")

        # --- START OF MODIFICATION ---
        # The query now checks the 'due_date' field instead of 'check_date'.
        due_transactions = db.transactions.find({
            "due_date": {"$gte": today_start, "$lt": today_end},
            "status": "Pending"
        })
        # --- END OF MODIFICATION ---

        count = 0
        for transaction in due_transactions:
            count += 1
            username = transaction['username']
            trans_name = transaction.get('name', 'a transaction')
            
            title = "Pending Transaction Due Today"
            message = f"Reminder: Your pending transaction for '{trans_name}' is due today. Please review and complete the remaining details."
            url = url_for('main.transactions_pending', _external=False)

            # Add the notification to the database
            add_notification(username, title, message, url)
            print(f"  - Created notification for user '{username}' regarding '{trans_name}'.")
        
        if count == 0:
            print("No transactions due today.")
        else:
            print(f"Successfully created {count} notifications.")

# --- START OF NEW FUNCTION ---
def check_upcoming_schedules_and_notify():
    """
    Scans for schedules starting today and creates reminder notifications for the respective users.
    """
    with app.app_context():
        db = app.db
        if db is None:
            print("Error: Database connection not available for schedules check.")
            return

        today_start = datetime.now(pytz.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        today_end = today_start + timedelta(days=1)
        
        print(f"Checking for schedules starting between {today_start} and {today_end}...")

        upcoming_schedules = db.schedules.find({
            "start": {"$gte": today_start, "$lt": today_end}
        })

        count = 0
        for schedule in upcoming_schedules:
            count += 1
            username = schedule['username']
            schedule_title = schedule.get('title', 'an untitled event')
            
            title = "Upcoming Schedule Reminder"
            message = f"Reminder: Your event '{schedule_title}' is scheduled for today."
            url = url_for('main.schedules', _external=False)

            add_notification(username, title, message, url)
            print(f"  - Created schedule reminder for user '{username}' regarding '{schedule_title}'.")
        
        if count == 0:
            print("No schedules starting today.")
        else:
            print(f"Successfully created {count} schedule reminders.")
# --- END OF NEW FUNCTION ---


if __name__ == '__main__':
    check_due_transactions_and_notify()
    print("\n" + "="*30 + "\n")
    check_upcoming_schedules_and_notify()