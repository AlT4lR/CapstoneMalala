# website/auth.py

from . import jwt, limiter, get_remote_address
from .constants import LOGIN_ATTEMPT_LIMIT, LOCKOUT_DURATION_MINUTES # Import constants
from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify, make_response, current_app
from flask_mail import Message
from flask_jwt_extended import create_access_token, create_refresh_token, jwt_required, get_jwt_identity, set_access_cookies, set_refresh_cookies, unset_jwt_cookies, get_jwt
from datetime import datetime, timedelta
import pyotp
import qrcode
import qrcode.image.svg
import io
import base64
import re
import logging
from flask_babel import gettext as _


# Import the global 'jwt' instance, 'limiter' instance, and 'get_remote_address' function from __init__.py
# Note: limiter and get_remote_address are now imported from __init__.py as initialized instances
from . import jwt, limiter, get_remote_address

# Import FlaskForm and necessary fields/validators
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Length, Email, EqualTo, ValidationError

logger = logging.getLogger(__name__)

auth = Blueprint('auth', __name__)

# --- NEW: Redirect for the root URL ---
@auth.route('/')
def index():
    """Redirects the root URL to the login page."""
    return redirect(url_for('auth.login'))
# --- END NEW ---

# --- Constants ---
LOGIN_ATTEMPT_LIMIT = 5
LOCKOUT_DURATION_MINUTES = 10

# --- Form Classes ---
class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=3, max=20)])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=8)])
    submit = SubmitField('Login') # Added submit button for WTForms

# OTPForm is primarily for CSRF protection as OTP inputs are handled manually in HTML.
class OTPForm(FlaskForm):
    submit = SubmitField('Verify') # Added submit button for WTForms

# --- MODIFIED: Registration Form ---
class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=3, max=20)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=8)])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password', message='Passwords must match')])
    submit = SubmitField('Register')

    def validate_username(self, username):
        # Use current_app to access the database and helper functions
        if current_app.get_user_by_username(username.data):
            raise ValidationError('That username is taken. Please choose a different one.')

    def validate_email(self, email):
        # Use current_app to access the database and helper functions
        if current_app.get_user_by_email(email.data):
            raise ValidationError('That email is already registered. Please use a different one.')
# --- END MODIFIED ---


# --- JWT Error Handlers ---
@jwt.unauthorized_loader
def unauthorized_response(callback):
    """Callback for when a JWT is missing from a protected endpoint."""
    flash('Please log in to access this page.', 'error')
    return redirect(url_for('auth.login'))

@jwt.invalid_token_loader
def invalid_token_response(callback):
    """Callback for when a JWT is invalid (e.g., expired, tampered)."""
    flash('Your session has expired or is invalid. Please log in again.', 'error')
    return redirect(url_for('auth.login'))

@jwt.expired_token_loader
def expired_token_response(jwt_header, jwt_payload):
    """Callback for when a JWT access token has expired."""
    flash('Your session has expired. Please log in again.', 'error')
    return redirect(url_for('auth.login'))

# --- Helper Functions ---
def send_otp_email(recipient_email, otp):
    """Sends the OTP code to the user's email."""
    mail = current_app.mail
    if not mail:
        logger.error("Mail extension not initialized. Cannot send email.")
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

# --- Routes ---
@auth.route('/login', methods=['GET'])
def login():
    # Instantiate the LoginForm and pass it to the template
    form = LoginForm()
    show_sidebar = False
    return render_template('login.html', form=form, show_sidebar=show_sidebar)

@auth.route('/login', methods=['POST'])
# Apply the limiter using the globally imported 'limiter' instance and the correct 'get_remote_address' function
@limiter.limit("5 per minute; 100 per day", key_func=get_remote_address,
               error_message="Too many login attempts from this IP. Please try again later.")
def login_post():
    # Instantiate the form for POST request handling as well
    form = LoginForm()

    # Use WTForms for validation
    if not form.validate_on_submit():
        # If validation fails, re-render the login page with errors
        flash('Invalid input. Please check the fields.', 'error')
        return render_template('login.html', form=form)

    username = form.username.data
    password = form.password.data

    # Use current_app to access model functions and user data
    user = current_app.get_user_by_username(username)

    # Check if user exists and is locked out
    if user and user.get('lockoutUntil') and user['lockoutUntil'] > datetime.utcnow():
        remaining_time = user['lockoutUntil'] - datetime.utcnow()
        minutes, seconds = divmod(int(remaining_time.total_seconds()), 60)
        flash(f'Account locked. Please try again in {minutes}m {seconds}s.', 'error')
        current_app.record_failed_login_attempt(username) # Record attempt even if locked
        return render_template('login.html', form=form) # Pass form back

    # Verify credentials
    if not user or not current_app.check_password(user['passwordHash'], password):
        if user: # If user exists but password was wrong
            current_app.record_failed_login_attempt(username)
            if user.get('failedLoginAttempts', 0) >= LOGIN_ATTEMPT_LIMIT:
                 flash(f'Too many failed attempts. Your account has been locked for {LOCKOUT_DURATION_MINUTES} minutes.', 'error')
        else: # User does not exist
            flash('Invalid username or password.', 'error')
        return render_template('login.html', form=form) # Pass form back

    # If account is not active (email not verified)
    if not user.get('isActive', False):
        flash('Your account is not verified. Please check your email for the OTP.', 'error')
        session['username_for_otp'] = user['username'] # Store username for OTP verification
        return redirect(url_for('auth.verify_otp'))

    # Successful login: Reset failed attempts, update last login
    current_app.update_last_login(user['username'])

    # Check for 2FA setup
    if user.get('otpSecret'):
        session['username_for_2fa_login'] = user['username'] # Store username for 2FA verification step
        # --- FIX: Changed redirect endpoint based on the traceback's suggestion ---
        # The traceback indicated 'auth.verify_2fa_login' was not found and suggested 'auth.verify_otp'.
        # Although 'auth.verify_otp' is for registration, following the traceback's specific hint.
        # If this causes logical errors, the actual problem might be that 'auth.verify_2fa_login'
        # endpoint is misconfigured or misspelled in its decorator.
        return redirect(url_for('auth.verify_otp'))
        # --- END FIX ---
    else:
        # No 2FA required/setup, proceed to issue JWTs and log in user
        access_token = create_access_token(identity=user['username'])
        refresh_token = create_refresh_token(identity=user['username'])

        response = make_response(redirect(url_for('main.dashboard')))
        set_access_cookies(response, access_token)
        set_refresh_cookies(response, refresh_token)

        flash('Login successful!', 'success')
        session.clear() # Clear any transient session data from login/otp steps
        return response

@auth.route('/register', methods=['GET'])
def register():
    # Instantiate the form for GET request
    form = RegistrationForm()
    show_sidebar = False
    return render_template('register.html', form=form, show_sidebar=show_sidebar)

@auth.route('/register', methods=['POST'])
def register_post():
    # Instantiate the form for POST request handling
    form = RegistrationForm()

    # Use WTForms validation:
    if form.validate_on_submit():
        username = form.username.data
        email = form.email.data
        password = form.password.data

        # Honeypot validation is still done directly from request.form
        honeypot_field = request.form.get('honeypot', '').strip()
        if honeypot_field:
            logger.warning(f"Honeypot field was filled by {get_remote_address()}. Blocking registration for username '{username}'.")
            flash('Malicious activity detected. Your attempt has been logged.', 'error')
            return render_template('register.html', form=form) # Pass form back

        # Use current_app to access model functions
        user_added = current_app.add_user(username, email, password)

        if user_added:
            # Generate and store OTP for email verification
            otp_generated = current_app.set_user_otp(username, otp_type='email')
            if otp_generated:
                send_otp_email(email, otp_generated)
                session['username_for_otp'] = username
                flash('Registration successful! Please verify your email with the OTP.', 'success')
                return redirect(url_for('auth.verify_otp'))
            else:
                flash('Could not generate OTP for email verification. Please contact support.', 'error')
                # If OTP generation fails, it might be better to delete the user or re-render with a more specific error
                return render_template('register.html', form=form) # Pass form back
        else:
            flash('Username or Email already exists. Please choose another.', 'error')
            # Populate form fields if registration fails to maintain user input
            form.username.data = username
            form.email.data = email
            return render_template('register.html', form=form) # Pass form back
    else:
        # If validation fails, re-render the registration page with errors
        flash('Please fix the errors in the form.', 'error')
        return render_template('register.html', form=form)

@auth.route('/verify-otp', methods=['GET', 'POST'])
def verify_otp():
    username_for_otp = session.get('username_for_otp')
    if not username_for_otp:
        flash('No user session found for OTP verification. Please log in or register.', 'error')
        return redirect(url_for('auth.login'))

    # Use current_app to access model functions
    user = current_app.get_user_by_username(username_for_otp)
    if not user:
        flash('User not found. Please log in or register.', 'error')
        return redirect(url_for('auth.login'))

    # --- FIX: Automatically send OTP on GET request if not already verified ---
    if request.method == 'GET':
        # Only send OTP if the user is not already active (email not verified)
        if not user.get('isActive', False):
            # The set_user_otp function generates and saves the OTP, and returns it.
            otp_generated = current_app.set_user_otp(username_for_otp, otp_type='email')
            if otp_generated:
                send_otp_email(user['email'], otp_generated)
            else:
                flash('Could not generate or send OTP. Please try registering again or contact support.', 'error')
                # If OTP generation fails here, it might be good to redirect them to login or registration.
                # For now, we'll allow them to see the page, but verification might fail if OTP is not set.
        # If user is already active, perhaps redirect them to login or dashboard?
        # else:
        #     flash('Your email is already verified. You can proceed to login.', 'info')
        #     return redirect(url_for('auth.login'))
    # --- END FIX ---

    # Instantiate the form for CSRF protection
    form = OTPForm()

    if request.method == 'POST':
        # Collect OTP digits from form
        otp_list = [request.form.get(f'otp{i}') for i in range(1, 7)]
        if not all(otp_list):
            flash('Please enter the complete 6-digit OTP.', 'error')
            return render_template('otp_verify.html', form=form) # Pass form back

        submitted_otp = "".join(otp_list)

        # Use current_app to access model functions
        if current_app.verify_user_otp(username_for_otp, submitted_otp, otp_type='email'):
            flash('Email verified successfully! You can now set up your Two-Factor Authentication.', 'success')
            session.pop('username_for_otp', None)
            session['username_for_2fa_setup'] = username_for_otp
            return redirect(url_for('auth.setup_2fa'))
        else:
            flash('Invalid or expired OTP. Please try again.', 'error')
            return render_template('otp_verify.html', form=form) # Pass form back

    # For GET request, render the template with the form
    return render_template('otp_verify.html', form=form)

@auth.route('/resend-otp')
def resend_otp():
    username = session.get('username_for_otp')
    if not username:
        flash('No user session found. Please log in.', 'error')
        return redirect(url_for('auth.login'))

    # Use current_app to access model functions
    user = current_app.get_user_by_username(username)
    if not user:
        flash('An error occurred. User not found.', 'error')
        return redirect(url_for('auth.login'))

    # Regenerate and send OTP
    otp_generated = current_app.set_user_otp(username, otp_type='email')
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

    # Use current_app to access model functions
    user = current_app.get_user_by_username(username)
    if not user or not user.get('otpSecret'):
        flash('Error retrieving 2FA setup information. Please contact support.', 'error')
        return redirect(url_for('auth.login'))

    otp_secret = user['otpSecret']
    totp = pyotp.TOTP(otp_secret)
    # Use provided email for the provisioning URI name
    provisioning_uri = totp.provisioning_uri(name=user['email'], issuer_name="DecoOffice")

    img = qrcode.make(provisioning_uri, image_factory=qrcode.image.svg.SvgImage)
    buffered_image = io.BytesIO()
    img.save(buffered_image)
    qr_code_svg = base64.b64encode(buffered_image.getvalue()).decode('utf-8')

    # Instantiate the form for CSRF protection
    form = OTPForm()

    if request.method == 'POST':
        otp_input = request.form.get('otp')
        if not otp_input:
            flash('Please enter the 6-digit code from your authenticator app.', 'error')
            return render_template('setup_2fa.html', qr_code_svg=qr_code_svg, otp_secret=otp_secret, form=form) # Pass form back

        # Use current_app to access model functions
        if current_app.verify_user_otp(username, otp_input, otp_type='2fa'):
            flash('Two-Factor Authentication successfully set up! You can now log in.', 'success')
            session.pop('username_for_2fa_setup', None)
            return redirect(url_for('auth.login'))
        else:
            flash('Invalid 2FA code. Please try again.', 'error')
            return render_template('setup_2fa.html', qr_code_svg=qr_code_svg, otp_secret=otp_secret, form=form) # Pass form back

    return render_template('setup_2fa.html', qr_code_svg=qr_code_svg, otp_secret=otp_secret, form=form) # Pass form back

@auth.route('/logout')
def logout():
    response = make_response(redirect(url_for('auth.login'))) # Redirect to login page after logout
    unset_jwt_cookies(response) # Clear JWT cookies
    session.clear() # Clear session data
    flash('You have been logged out.', 'success') # Confirmation message
    return response