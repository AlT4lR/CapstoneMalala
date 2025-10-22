# check_scheduled_events_task.py
import os
from datetime import datetime, timedelta
import pytz
from website import create_app
from website.models import add_notification
from flask import url_for

# Initialize the Flask app to get access to its context
app = create_app(os.getenv('FLASK_CONFIG') or 'dev')

def check_scheduled_events_and_notify():
    """
    Scans for events scheduled for the current day and creates reminder notifications.
    """
    with app.app_context():
        db = app.db
        if db is None:
            print("Error: Database connection not available.")
            return

        # Define today's date range in UTC
        today_start = datetime.now(pytz.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        today_end = today_start + timedelta(days=1)
        
        print(f"Checking for scheduled events between {today_start} and {today_end}...")

        # Find all schedules where the start time is today
        due_events = db.schedules.find({
            "start": {"$gte": today_start, "$lt": today_end}
        })

        count = 0
        for event in due_events:
            count += 1
            username = event['username']
            event_title = event.get('title', 'an event')
            
            # Prepare notification details
            title = "Event Reminder"
            message = f"Reminder: Your event '{event_title}' is scheduled for today."
            url = url_for('main.schedules', _external=False)

            # Add the notification to the database for the user
            add_notification(username, title, message, url)
            print(f"  - Created reminder for user '{username}' regarding event '{event_title}'.")
        
        if count == 0:
            print("No events scheduled for today.")
        else:
            print(f"Successfully created {count} event reminders.")


if __name__ == '__main__':
    check_scheduled_events_and_notify()