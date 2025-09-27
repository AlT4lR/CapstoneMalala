# create_notifications_task.py
import os
from datetime import datetime, timedelta
import pytz
from website import create_app
from website.models import add_notification
from pywebpush import webpush, WebPushException
import json

# Use the 'prod' config for the task, or a custom 'task' config if you create one
app = create_app(os.getenv('FLASK_CONFIG') or 'prod')

def check_due_transactions_and_notify():
    """
    Scans for transactions due today and creates notifications and sends push messages.
    """
    with app.app_context():
        db = app.db
        if db is None:
            print("Error: Database connection not available.")
            return

        print("Starting notification task...")
        # Define the start and end of today in UTC
        today_start = datetime.now(pytz.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        today_end = today_start + timedelta(days=1)
        
        # Find transactions with a check_date of today that are still pending
        due_transactions = db.transactions.find({
            "check_date": {
                "$gte": today_start,
                "$lt": today_end
            },
            "status": "Pending"
        })

        processed_users = set()
        for transaction in due_transactions:
            username = transaction['username']
            
            # To avoid sending multiple notifications for multiple due transactions on the same day,
            # we can create a summary. Or send one for each. Here we send one for each.
            message = f"Reminder: Transaction #{transaction['check_no']} for ₱{transaction['amount']:,.2f} is due today."
            url = '/transactions/pending' # URL to open on click

            # 1. Create the in-app (bell) notification
            add_notification(username, message, url)
            print(f"Created in-app notification for {username}.")
            
            # 2. Send PWA Push Notifications
            user = db.users.find_one({'username': username})
            if user and 'push_subscriptions' in user:
                for sub in user['push_subscriptions']:
                    try:
                        webpush(
                            subscription_info=sub,
                            data=json.dumps({
                                "title": "Transaction Due Today",
                                "body": message,
                                "url": url
                            }),
                            vapid_private_key=app.config['VAPID_PRIVATE_KEY'],
                            vapid_claims={"sub": app.config['VAPID_CLAIM_EMAIL']}
                        )
                        print(f"Sent push notification to {username}")
                    except WebPushException as ex:
                        print(f"Error sending push to {username}: {ex}")
                        # If subscription is expired or invalid, remove it from the DB
                        if ex.response and ex.response.status_code in [404, 410]:
                            db.users.update_one({'username': username}, {'$pull': {'push_subscriptions': sub}})
                            print(f"Removed expired subscription for {username}")
        
        print("Notification task finished.")

if __name__ == '__main__':
    check_due_transactions_and_notify()