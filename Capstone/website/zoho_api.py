# website/zoho_api.py
import requests
from flask import current_app, url_for
from urllib.parse import urlencode
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

def get_auth_url():
    """Generates the Zoho OAuth 2.0 authorization URL."""
    params = {
        'response_type': 'code',
        'client_id': current_app.config['ZOHO_CLIENT_ID'],
        'scope': 'ZohoCalendar.events.ALL,ZohoCalendar.calendars.ALL',
        'redirect_uri': current_app.config['ZOHO_REDIRECT_URI'],
        'access_type': 'offline', # To get a refresh token
        'prompt': 'consent'
    }
    auth_url = f"{current_app.config['ZOHO_ACCOUNTS_BASE_URL']}/auth?{urlencode(params)}"
    return auth_url

def exchange_code_for_tokens(code):
    """Exchanges an authorization code for access and refresh tokens."""
    try:
        response = requests.post(
            f"{current_app.config['ZOHO_ACCOUNTS_BASE_URL']}/token",
            data={
                'code': code,
                'client_id': current_app.config['ZOHO_CLIENT_ID'],
                'client_secret': current_app.config['ZOHO_CLIENT_SECRET'],
                'redirect_uri': current_app.config['ZOHO_REDIRECT_URI'],
                'grant_type': 'authorization_code'
            }
        )
        response.raise_for_status()
        token_data = response.json()
        
        # Calculate expiry time
        if 'expires_in' in token_data:
            token_data['expires_at'] = datetime.utcnow() + timedelta(seconds=token_data['expires_in'] - 60) # 60s buffer
            
        return token_data
    except requests.exceptions.RequestException as e:
        logger.error(f"Zoho token exchange failed: {e.response.text if e.response else e}")
        return None

def get_calendars(access_token):
    """Fetches the user's calendars from Zoho."""
    try:
        response = requests.get(
            f"{current_app.config['ZOHO_API_BASE_URL']}/calendars",
            headers={'Authorization': f'Zoho-oauthtoken {access_token}'}
        )
        response.raise_for_status()
        return response.json().get('calendars', [])
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to fetch Zoho calendars: {e.response.text if e.response else e}")
        return None

def get_events(access_token, calendar_id, start_date, end_date):
    """Fetches events from a specific Zoho calendar within a date range."""
    try:
        params = {
            'start_date': start_date.strftime('%Y-%m-%dT%H:%M:%S%z'),
            'end_date': end_date.strftime('%Y-%m-%dT%H:%M:%S%z')
        }
        response = requests.get(
            f"{current_app.config['ZOHO_API_BASE_URL']}/calendars/{calendar_id}/events",
            headers={'Authorization': f'Zoho-oauthtoken {access_token}'},
            params=params
        )
        response.raise_for_status()
        return response.json().get('events', [])
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to fetch Zoho events: {e.response.text if e.response else e}")
        return []

def create_event(access_token, calendar_id, event_data):
    """Creates a new event in a Zoho calendar."""
    try:
        # Transform our app's event data into Zoho's format
        zoho_event = {
            "title": event_data.get('title'),
            "description": event_data.get('notes'),
            "start_time": event_data.get('start'),
            "end_time": event_data.get('end'),
            # You can add more fields here like reminders, attendees, etc.
        }
        response = requests.post(
            f"{current_app.config['ZOHO_API_BASE_URL']}/calendars/{calendar_id}/events",
            headers={'Authorization': f'Zoho-oauthtoken {access_token}'},
            json={"events": [zoho_event]}
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to create Zoho event: {e.response.text if e.response else e}")
        return None