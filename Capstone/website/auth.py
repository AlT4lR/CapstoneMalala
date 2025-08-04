# website/auth.py

from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify, make_response, current_app
from flask_mail import Message
from flask_jwt_extended import create_access_token, create_refresh_token, jwt_required, get_jwt_identity, set_access_cookies, set_refresh_cookies, unset_jwt_cookies, get_jwt
from datetime import datetime, timedelta
import jwt
import pyotp
import qrcode
import qrcode.image.svg
import io
import base64
import re
import logging

logger = logging.getLogger(__name__)

auth = Blueprint('auth', __name__)

# Access extensions via current_app in request context or app object in app factory
# No need for get_mail(), get_jwt(), get_limiter() globals if initialized with app.

# Configure lockout parameters
LOGIN_ATTEMPT_LIMIT = 5
LOCKOUT_DURATION_MINUTES = 10

# --- JWT Error Handlers ---
@jwt.unauthorized_loader
def unauthorized_response(callback):
    """Callback for missing JWT."""
    flash('Please log in to access this page.', 'error')
    return redirect(url_for('auth.login'))

@jwt.invalid_token_loader
def invalid_token_response(callback):
    """Callback for invalid JWT."""
    flash('Your session has expired or is invalid. Please log in again.', 'error')
    return redirect(url_for('auth.login'))

@jwt.expired_token_loader
def expired_token_response(jwt_header, jwt_payload):
    """Callback for expired JWT."""
    flash('Your session has expired. Please log in again.', 'error')
    return redirect(url_for('auth.login'))

# --- Helper Functions ---
def send_otp_email(recipient_email, otp):
    """Sends the OTP code to the user's email."""
    mail = current_app.mail # Access mail via current_app
    if not mail:
        logger.error("Mail extension is not initialized. Cannot send email.")
        flash('Could not send OTP email due to a server configuration error.', 'error')
        return

    try:
        msg = Message(
            subject="Your DecoOffice Verification Code",
            recipients=[recipient_email],
            body=f"Welcome to DecoOffice!\n\nYour one-time password (OTP) is: {otp}\n\nThis code will expire in 10 minutes. Please do not share it with anyone.\n\nIf you did not request this, please ignore this email.\n\nBest regards,\nThe DecoOffice Team"
        )
        mail.send(msg)
        logger.info(f"Successfully sent OTP to {recipient_email}")
        flash('A new OTP has been sent to your email address.', 'success')
    except Exception as e:
        logger.error(f"Failed to send email to {recipient_email}: {e}")
        flash('Failed to send OTP email. Please try again later.', 'error')

def get_remote_addr():
    """Returns the remote IP address of the client making the request."""
    return request.remote_addr

# --- Routes ---
@auth.route('/login', methods=['GET'])
def login():
    return render_template('login.html')

@auth.route('/login', methods=['POST'])
@current_app.limiter.limit("5 per minute", key_func=get_remote_addr) # Access limiter via current_app
def login_post():
    username = request.form.get('username')
    password = request.form.get('password')

    user = current_app.get_user_by_username(username) # Access user model function via app proxy

    # Check if user exists and is locked out
    if user and user.get('lockoutUntil') and user['lockoutUntil'] > datetime.utcnow():
        remaining_time = user['lockoutUntil'] - datetime.utcnow()
        minutes, seconds = divmod(int(remaining_time.total_seconds()), 60)
        flash(f'Account locked. Please try again in {minutes}m {seconds}s.', 'error')
        current_app.record_failed_login_attempt(username) # Access model function via app proxy
        return redirect(url_for('auth.login'))

    if not user or not current_app.check_password(user['passwordHash'], password): # Access model function via app proxy
        if user:
            current_app.record_failed_login_attempt(username) # Access model function via app proxy
            if user.get('failedLoginAttempts', 0) >= LOGIN_ATTEMPT_LIMIT:
                 flash(f'Too many failed attempts. Your account has been locked for {LOCKOUT_DURATION_MINUTES} minutes.', 'error')
        else:
            flash('Invalid username or password.', 'error')
        return redirect(url_for('auth.login'))

    # If account is not active (email not verified)
    if not user.get('isActive', False):
        flash('Your account is not verified. Please check your email for the OTP.', 'error')
        session['username_for_otp'] = user['username']
        return redirect(url_for('auth.verify_otp'))

    # Password correct, reset failed login attempts and update last login
    current_app.update_last_login(user['username']) # Access model function via app proxy

    # Check for 2FA setup
    if user.get('otpSecret'):
        session['username_for_2fa_login'] = user['username']
        return redirect(url_for('auth.verify_2fa_login'))
    else:
        # Active user, no 2FA setup, issue JWTs
        access_token = create_access_token(identity=user['username'])
        refresh_token = create_refresh_token(identity=user['username'])

        response = make_response(redirect(url_for('main.dashboard')))
        set_access_cookies(response, access_token)
        set_refresh_cookies(response, refresh_token)
        
        flash('Login successful!', 'success')
        session.clear() # Clear session data related to login/otp steps
        return response

@auth.route('/register', methods=['GET'])
def register():
    return render_template('register.html')

@auth.route('/register', methods=['POST'])
def register_post():
    username = request.form.get('username')
    email = request.form.get('email')
    password = request.form.get('password')

    if not all([username, email, password]):
        flash('All fields are required.', 'error')
        return render_template('register.html', username=username, email=email)

    # Password validation (assuming same rules as before)
    if len(password) < 8 or \
       not re.search(r"[a-z]", password) or \
       not re.search(r"[A-Z]", password) or \
       not re.search(r"[0-9]", password) or \
       not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
        flash('Password must be at least 8 characters long and contain at least one uppercase letter, one lowercase letter, one number, and one special character.', 'error')
        return render_template('register.html', username=username, email=email)

    if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
        flash('Invalid email address.', 'error')
        return render_template('register.html', username=username, email=email)

    user_added = current_app.add_user(username, email, password) # Access model function via app proxy

    if user_added:
        otp_generated = current_app.set_user_otp(username, otp_type='email') # Access model function via app proxy
        if otp_generated:
            send_otp_email(email, otp_generated)
            session['username_for_otp'] = username
            flash('Registration successful! Please verify your email with the OTP.', 'success')
            return redirect(url_for('auth.verify_otp'))
        else:
            flash('Could not generate OTP for email verification. Please contact support.', 'error')
            return render_template('register.html', username=username, email=email)
    else:
        flash('Username or Email already exists. Please choose another.', 'error')
        return render_template('register.html', username=username, email=email)

@auth.route('/verify-otp', methods=['GET', 'POST'])
def verify_otp():
    username_for_otp = session.get('username_for_otp')
    if not username_for_otp:
        flash('No user session found for OTP verification. Please log in or register.', 'error')
        return redirect(url_for('auth.login'))

    user = current_app.get_user_by_username(username_for_otp) # Access model function via app proxy
    if not user:
        flash('User not found. Please log in or register.', 'error')
        return redirect(url_for('auth.login'))

    if request.method == 'POST':
        otp_list = [request.form.get(f'otp{i}') for i in range(1, 7)]
        if not all(otp_list):
            flash('Please enter the complete 6-digit OTP.', 'error')
            return render_template('otp_verify.html')

        submitted_otp = "".join(otp_list)

        if current_app.verify_user_otp(username_for_otp, submitted_otp, otp_type='email'): # Access model function via app proxy
            flash('Email verified successfully! You can now set up your Two-Factor Authentication.', 'success')
            session.pop('username_for_otp', None)
            session['username_for_2fa_setup'] = username_for_otp
            return redirect(url_for('auth.setup_2fa'))
        else:
            flash('Invalid or expired OTP. Please try again.', 'error')
            return render_template('otp_verify.html')

    return render_template('otp_verify.html')

@auth.route('/resend-otp')
def resend_otp():
    username = session.get('username_for_otp')
    if not username:
        flash('No user session found. Please log in.', 'error')
        return redirect(url_for('auth.login'))

    user = current_app.get_user_by_username(username) # Access model function via app proxy
    if not user:
        flash('An error occurred. User not found.', 'error')
        return redirect(url_for('auth.login'))

    otp_generated = current_app.set_user_otp(username, otp_type='email') # Access model function via app proxy
    if otp_generated:
        send_otp_email(user['email'], otp_generated)
    else:
        flash('Could not generate a new OTP. Please try again later.', 'error')

    return redirect(url_for('auth.verify_otp'))

@auth.route('/setup-2fa', methods=['GET', 'POST'])
def setup_2fa():
    username = session.get('username_for_2fa_setup')
    if not username:
        flash('Authentication required to set up 2FA.', 'error')
        return redirect(url_for('auth.login'))

    user = current_app.get_user_by_username(username) # Access model function via app proxy
    if not user or not user.get('otpSecret'):
        flash('Error retrieving 2FA setup information. Please contact support.', 'error')
        return redirect(url_for('auth.login'))

    otp_secret = user['otpSecret']
    totp = pyotp.TOTP(otp_secret)
    provisioning_uri = totp.provisioning_uri(name=user['email'], issuer_name="DecoOffice")

    img = qrcode.make(provisioning_uri, image_factory=qrcode.image.svg.SvgImage)
    buffered_image = io.BytesIO()
    img.save(buffered_image)
    qr_code_svg = base64.b64encode(buffered_image.getvalue()).decode('utf-8')

    if request.method == 'POST':
        otp_input = request.form.get('otp')
        if not otp_input:
            flash('Please enter the 6-digit code from your authenticator app.', 'error')
            return render_template('setup_2fa.html', qr_code_svg=qr_code_svg, otp_secret=otp_secret)

        if current_app.verify_user_otp(username, otp_input, otp_type='2fa'): # Access model function via app proxy
            flash('Two-Factor Authentication successfully set up! You can now log in.', 'success')
            session.pop('username_for_2fa_setup', None)
            return redirect(url_for('auth.login'))
        else:
            flash('Invalid 2FA code. Please try again.', 'error')
            return render_template('setup_2fa.html', qr_code_svg=qr_code_svg, otp_secret=otp_secret)

    return render_template('setup_2fa.html', qr_code_svg=qr_code_svg, otp_secret=otp_secret)

@auth.route('/verify-2fa-login', methods=['GET', 'POST'])
def verify_2fa_login():
    username = session.get('username_for_2fa_login')
    if not username:
        flash('Authentication session expired. Please log in again.', 'error')
        return redirect(url_for('auth.login'))

    user = current_app.get_user_by_username(username) # Access model function via app proxy
    if not user or not user.get('otpSecret'):
        flash('2FA not configured for this account. Please log in normally.', 'error')
        session.pop('username_for_2fa_login', None)
        return redirect(url_for('auth.login'))

    if request.method == 'POST':
        otp_input = request.form.get('otp')
        if not otp_input:
            flash('Please enter the 6-digit code from your authenticator app.', 'error')
            return render_template('verify_2fa_login.html', username=username)

        if current_app.verify_user_otp(username, otp_input, otp_type='2fa'): # Access model function via app proxy
            access_token = create_access_token(identity=username)
            refresh_token = create_refresh_token(identity=username)

            response = make_response(redirect(url_for('main.dashboard')))
            set_access_cookies(response, access_token)
            set_refresh_cookies(response, refresh_token)
            
            flash('Login successful!', 'success')
            session.pop('username_for_2fa_login', None)
            return response
        else:
            flash('Invalid 2FA code. Please try again.', 'error')
            current_app.record_failed_login_attempt(username) # Access model function via app proxy
            return render_template('verify_2fa_login.html', username=username)

    return render_template('verify_2fa_login.html', username=username)

@auth.route('/logout')
def logout():
    response = make_response(redirect(url_for('auth.login')))
    unset_jwt_cookies(response)
    session.clear()
    flash('You have been logged out.', 'success')
    return response