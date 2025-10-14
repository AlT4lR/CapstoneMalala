# create_notifications_task.py
import os
from datetime import datetime, timedelta
import pytz
from website import create_app
from website.models import add_notification
from pywebpush import webpush, WebPushException
import json

app = create_app(os.getenv('FLASK_CONFIG') or 'prod')

def check_due_transactions_and_notify():
    with app.app_context():
        db = app.db
        if db is None:
            print("Error: Database connection not available.")
            return

        today_start = datetime.now(pytz.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        today_end = today_start + timedelta(days=1)
        
        due_transactions = db.transactions.find({
            "check_date": {"$gte": today_start, "$lt": today_end},
            "status": "Pending"
        })

        for transaction in due_transactions:
            username = transaction['username']
            message = f"Reminder: Transaction #{transaction['check_no']} is due today."
            url = '/transactions/pending'

            add_notification(username, "Transaction Due", message, url)
            
            user = db.users.find_one({'username': username})
            if user and 'push_subscriptions' in user:
                for sub in user['push_subscriptions']:
                    try:
                        webpush(
                            subscription_info=sub,
                            data=json.dumps({"title": "Transaction Due Today", "body": message, "url": url}),
                            vapid_private_key=app.config['VAPID_PRIVATE_KEY'],
                            vapid_claims={"sub": app.config['VAPID_CLAIM_EMAIL']}
                        )
                    except WebPushException as ex:
                        if ex.response and ex.response.status_code in [404, 410]:
                            db.users.update_one({'username': username}, {'$pull': {'push_subscriptions': sub}})

if __name__ == '__main__':
    check_due_transactions_and_notify()