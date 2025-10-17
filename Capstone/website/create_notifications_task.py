# create_notifications_task.py
import os
from datetime import datetime, timedelta
import pytz
from website import create_app
from website.models import add_notification, get_user_push_subscriptions # Modified import
from flask import url_for
# --- START OF MODIFICATION: Add imports for push notifications ---
from pywebpush import webpush, WebPushException
import json
# --- END OF MODIFICATION ---

app = create_app(os.getenv('FLASK_CONFIG') or 'dev')

def check_due_transactions_and_notify():
    with app.app_context():
        db = app.db
        if db is None:
            print("Error: Database connection not available.")
            return

        today_start = datetime.now(pytz.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        today_end = today_start + timedelta(days=1)
        
        print(f"Checking for transactions due between {today_start} and {today_end}...")

        due_transactions = db.transactions.find({
            "check_date": {"$gte": today_start, "$lt": today_end},
            "status": "Pending"
        })

        count = 0
        for transaction in due_transactions:
            count += 1
            username = transaction['username']
            trans_name = transaction.get('name', 'a transaction')
            
            title = "Pending Transaction Due Today"
            message = f"Reminder: Your transaction for '{trans_name}' is due today."
            url = url_for('main.transactions_pending', _external=False)

            add_notification(username, title, message, url)
            print(f"  - Created in-app notification for user '{username}' regarding '{trans_name}'.")

            # --- START OF MODIFICATION: Send Push Notification Logic ---
            push_subscriptions = get_user_push_subscriptions(username)
            if not push_subscriptions:
                continue

            notification_payload = {
                "title": title,
                "body": message,
                "icon": "/static/imgs/icons/logo.ico",
                "data": {"url": url}
            }
            
            for sub in push_subscriptions:
                try:
                    webpush(
                        subscription_info=sub,
                        data=json.dumps(notification_payload),
                        vapid_private_key=app.config['VAPID_PRIVATE_KEY'],
                        vapid_claims={"sub": f"mailto:{app.config['VAPID_CLAIM_EMAIL']}"}
                    )
                    print(f"  - Sent push notification to a device for user '{username}'.")
                except WebPushException as ex:
                    print(f"  - Error sending push notification for user '{username}': {ex}")
                    # In a production app, you would handle expired/invalid subscriptions here,
                    # e.g., by removing them from the database.
            # --- END OF MODIFICATION ---
        
        if count == 0:
            print("No transactions due today.")
        else:
            print(f"Successfully processed {count} notifications.")

if __name__ == '__main__':
    check_due_transactions_and_notify()