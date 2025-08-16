# website/auth.py

from . import jwt, limiter, get_remote_address
from .constants import LOGIN_ATTEMPT_LIMIT, LOCKOUT_DURATION_MINUTES
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


from . import jwt, limiter, get_remote_address

from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Length, Email, EqualTo, ValidationError


logger = logging.getLogger(__name__)

auth = Blueprint('auth', __name__)

# --- Redirect for the root URL ---
@auth.route('/')
def index():
    """Redirects the root URL to the login page."""
    return redirect(url_for('auth.login'))

# --- Form Classes ---
class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=3, max=20)])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=8)])
    submit = SubmitField('Login')

class OTPForm(FlaskForm): # Used for both OTP verification and 2FA verification
    submit = SubmitField('Verify')

# --- Registration Form ---
class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=3, max=20)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=8)])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password', message='Passwords must match')])
    submit = SubmitField('Register')

    def validate_username(self, username):
        if current_app.get_user_by_username(username.data):
            raise ValidationError('That username is taken. Please choose a different one.')

    def validate_email(self, email):
        if current_app.get_user_by_email(email.data):
            raise ValidationError('That email is already registered. Please use a different one.')
# --- END MODIFIED ---


# --- JWT Error Handlers ---
@jwt.unauthorized_loader
def unauthorized_response(callback):
    flash('Please log in to access this page.', 'error')
    return redirect(url_for('auth.login'))

@jwt.invalid_token_loader
def invalid_token_response(callback):
    flash('Your session has expired or is invalid. Please log in again.', 'error')
    return redirect(url_for('auth.login'))

@jwt.expired_token_loader
def expired_token_response(jwt_header, jwt_payload):
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
    form = LoginForm()
    show_sidebar = False
    return render_template('login.html', form=form, show_sidebar=show_sidebar)

@auth.route('/login', methods=['POST'])
@limiter.limit("5 per minute; 100 per day", key_func=get_remote_address,
               error_message="Too many login attempts from this IP. Please try again later.")
def login_post():
    form = LoginForm()

    if not form.validate_on_submit():
        flash('Invalid input. Please check the fields.', 'error')
        return render_template('login.html', form=form)

    username = form.username.data
    password = form.password.data

    user = current_app.get_user_by_username(username)

    if user and user.get('lockoutUntil') and user['lockoutUntil'] > datetime.utcnow():
        remaining_time = user['lockoutUntil'] - datetime.utcnow()
        minutes, seconds = divmod(int(remaining_time.total_seconds()), 60)
        flash(f'Account locked. Please try again in {minutes}m {seconds}s.', 'error')
        current_app.record_failed_login_attempt(username)
        return render_template('login.html', form=form)

    if not user or not current_app.check_password(user['passwordHash'], password):
        if user:
            current_app.record_failed_login_attempt(username)
            if user.get('failedLoginAttempts', 0) >= LOGIN_ATTEMPT_LIMIT:
                 flash(f'Too many failed attempts. Your account has been locked for {LOCKOUT_DURATION_MINUTES} minutes.', 'error')
        else:
            flash('Invalid username or password.', 'error')
        return render_template('login.html', form=form)

    # If account not active (email not verified)
    if not user.get('isActive', False):
        flash('Your account is not verified. Please check your email for the OTP.', 'error')
        session['username_for_otp'] = username # Store username for OTP verification
        return redirect(url_for('auth.verify_otp'))

    # Successful login, reset attempts, update last login
    current_app.update_last_login(user['username'])

    # Check for 2FA setup
    if user.get('otpSecret'):
        session['username_for_2fa_login'] = user['username'] # Store username for 2FA verification step
        # Redirect to verify_otp, which will handle both email verification completion (if needed)
        # and 2FA verification. The template and logic inside verify_otp will adapt based on session.
        return redirect(url_for('auth.verify_otp'))
    else:
        # No 2FA required/setup, proceed to issue JWTs and log in user
        access_token = create_access_token(identity=user['username'])
        refresh_token = create_refresh_token(identity=user['username'])

        response = make_response(redirect(url_for('main.dashboard')))
        set_access_cookies(response, access_token)
        set_refresh_cookies(response, refresh_token)

        flash('Login successful!', 'success')
        session.clear() # Clear any transient session data
        return response

@auth.route('/register', methods=['GET'])
def register():
    form = RegistrationForm()
    show_sidebar = False
    return render_template('register.html', form=form, show_sidebar=show_sidebar)

@auth.route('/register', methods=['POST'])
def register_post():
    form = RegistrationForm()

    if form.validate_on_submit():
        username = form.username.data
        email = form.email.data
        password = form.password.data

        honeypot_field = request.form.get('honeypot', '').strip()
        if honeypot_field:
            logger.warning(f"Honeypot field was filled by {get_remote_address()}. Blocking registration for username '{username}'.")
            flash('Malicious activity detected. Your attempt has been logged.', 'error')
            return render_template('register.html', form=form)

        user_added = current_app.add_user(username, email, password)

        if user_added:
            otp_generated = current_app.set_user_otp(username, otp_type='email')
            if otp_generated:
                send_otp_email(email, otp_generated)
                session['username_for_otp'] = username # Store username for OTP verification
                flash('Registration successful! Please verify your email with the OTP.', 'success')
                return redirect(url_for('auth.verify_otp'))
            else:
                flash('Could not generate OTP for email verification. Please contact support.', 'error')
                return render_template('register.html', form=form)
        else:
            flash('Username or Email already exists. Please choose another.', 'error')
            form.username.data = username # Pre-fill fields on error
            form.email.data = email
            return render_template('register.html', form=form)
    else:
        flash('Please fix the errors in the form.', 'error')
        return render_template('register.html', form=form)

@auth.route('/verify-otp', methods=['GET', 'POST'])
def verify_otp():
    # Determine the context: is it for initial email verification or 2FA login?
    username_for_email_verification = session.get('username_for_otp')
    username_for_2fa_login = session.get('username_for_2fa_login')
    
    # The user is either coming from registration (username_for_otp) or from login requiring 2FA (username_for_2fa_login)
    username_in_context = username_for_email_verification or username_for_2fa_login

    # Define username_for_otp for use in the function
    username_for_otp = username_in_context

    if not username_in_context:
        # If no session data is found, redirect to login.
        flash('No user session found for OTP verification. Please log in or register.', 'error')
        return redirect(url_for('auth.login'))

    user = current_app.get_user_by_username(username_in_context)
    if not user:
        flash('User not found. Please log in or register.', 'error')
        # Clean up session data if user record is missing
        session.pop('username_for_otp', None)
        session.pop('username_for_2fa_login', None)
        return redirect(url_for('auth.login'))

    # --- Handle GET requests ---
    if request.method == 'GET':
        # If it's for email verification (user is not active)
        if not user.get('isActive', False) and username_for_email_verification:
            # Ensure we have a valid OTP to send
            otp_generated = current_app.set_user_otp(username_for_otp, otp_type='email')
            if otp_generated:
                send_otp_email(user['email'], otp_generated)
            else:
                flash('Could not generate or send OTP. Please try registering again or contact support.', 'error')
        # If it's for 2FA login, the OTP is expected via POST. GET simply renders the page.
        # The template will decide which UI to show based on the context.

    # Instantiate the form for CSRF protection
    form = OTPForm()

    # --- Handle POST requests ---
    if request.method == 'POST':
        otp_input = request.form.get('otp')
        if not otp_input:
            flash('Please enter the OTP.', 'error')
            # Re-render the page, indicating whether it's for 2FA or email verification
            return render_template('otp_verify.html', 
                                   form=form, 
                                   is_2fa_login=(username_for_2fa_login == username_for_otp))

        # Check if this is for 2FA login
        if username_for_2fa_login and username_for_2fa_login == username_for_otp:
            if current_app.verify_user_otp(username_for_otp, otp_input, otp_type='2fa'):
                flash('2FA Verified! Logging you in.', 'success')
                session.pop('username_for_2fa_login', None) # Clear 2FA login session
                
                # Generate JWTs and log the user in
                access_token = create_access_token(identity=username_for_otp)
                refresh_token = create_refresh_token(identity=username_for_otp)

                response = make_response(redirect(url_for('main.dashboard')))
                set_access_cookies(response, access_token)
                set_refresh_cookies(response, refresh_token)
                session.clear() # Clear all session data upon successful login
                return response
            else:
                flash('Invalid 2FA code. Please try again.', 'error')
                return render_template('otp_verify.html', form=form, is_2fa_login=True)
        else:
            # It's for email OTP verification after registration
            otp_list = [request.form.get(f'otp{i}') for i in range(1, 7)]
            if not all(otp_list):
                flash('Please enter the complete 6-digit OTP.', 'error')
                return render_template('otp_verify.html', form=form, is_2fa_login=False)
            
            submitted_otp = "".join(otp_list)

            if current_app.verify_user_otp(username_for_otp, submitted_otp, otp_type='email'):
                flash('Email verified successfully! You can now set up your Two-Factor Authentication.', 'success')
                session.pop('username_for_otp', None) # Clear email OTP session
                session['username_for_2fa_setup'] = username_for_otp # Prepare for 2FA setup
                return redirect(url_for('auth.setup_2fa'))
            else:
                flash('Invalid or expired OTP. Please try again.', 'error')
                return render_template('otp_verify.html', form=form, is_2fa_login=False)

    # Render the template. Pass context to help template adapt its UI.
    return render_template('otp_verify.html', 
                           form=form, 
                           is_2fa_login=(username_for_2fa_login == username_for_otp))

@auth.route('/resend-otp')
def resend_otp():
    # This route is primarily for email verification resend.
    username = session.get('username_for_otp')
    if not username:
        flash('No user session found for OTP resend. Please log in.', 'error')
        return redirect(url_for('auth.login'))

    user = current_app.get_user_by_username(username)
    if not user:
        flash('An error occurred. User not found.', 'error')
        session.pop('username_for_otp', None)
        return redirect(url_for('auth.login'))

    # Regenerate and send OTP for email verification
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

    user = current_app.get_user_by_username(username)
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

    form = OTPForm() # Using OTPForm for CSRF token

    if request.method == 'POST':
        otp_input = request.form.get('otp')
        if not otp_input:
            flash('Please enter the 6-digit code from your authenticator app.', 'error')
            return render_template('setup_2fa.html', qr_code_svg=qr_code_svg, otp_secret=otp_secret, form=form)

        if current_app.verify_user_otp(username, otp_input, otp_type='2fa'):
            flash('Two-Factor Authentication successfully set up! You can now log in.', 'success')
            session.pop('username_for_2fa_setup', None)
            return redirect(url_for('auth.login'))
        else:
            flash('Invalid 2FA code. Please try again.', 'error')
            return render_template('setup_2fa.html', qr_code_svg=qr_code_svg, otp_secret=otp_secret, form=form)

    return render_template('setup_2fa.html', qr_code_svg=qr_code_svg, otp_secret=otp_secret, form=form)

@auth.route('/logout')
def logout():
    response = make_response(redirect(url_for('auth.login')))
    unset_jwt_cookies(response)
    session.clear()
    flash('You have been logged out.', 'success')
    return response