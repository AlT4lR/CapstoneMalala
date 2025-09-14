# website/auth.py

from flask import Blueprint, render_template, request, redirect, url_for, session, flash, make_response, current_app
from flask_mail import Message
from flask_jwt_extended import create_access_token, create_refresh_token, jwt_required, get_jwt_identity, set_access_cookies, set_refresh_cookies, unset_jwt_cookies
from datetime import datetime, timedelta
import pyotp
import qrcode
import qrcode.image.svg
import io
import base64
import logging

from . import jwt, limiter
from .constants import LOGIN_ATTEMPT_LIMIT, LOCKOUT_DURATION_MINUTES
from .forms import LoginForm, RegistrationForm, OTPForm

logger = logging.getLogger(__name__)
auth = Blueprint('auth', __name__)

# --- JWT Error Handlers ---
# ... (error handlers remain unchanged) ...
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
# ... (send_otp_email remains unchanged) ...
def send_otp_email(recipient_email, otp):
    """Sends the OTP code to the user's email."""
    try:
        msg = Message("Your DecoOffice Verification Code", recipients=[recipient_email])
        msg.body = f"Welcome to DecoOffice!\n\nYour one-time password (OTP) is: {otp}\n\nThis code will expire in 10 minutes."
        current_app.mail.send(msg)
        logger.info(f"Successfully sent OTP to {recipient_email}")
        flash('A new OTP has been sent to your email address.', 'success')
    except Exception as e:
        logger.error(f"Failed to send email to {recipient_email}: {e}")
        flash('Failed to send OTP email. Please try again later.', 'error')


# --- Routes ---
@auth.route('/login', methods=['GET', 'POST'])
@limiter.limit("5 per minute")
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = current_app.get_user_by_username(form.username.data)

        if user and user.get('lockoutUntil') and user['lockoutUntil'] > datetime.utcnow():
            remaining = user['lockoutUntil'] - datetime.utcnow()
            flash(f'Account locked. Try again in {int(remaining.total_seconds() / 60)}m.', 'error')
            return render_template('login.html', form=form, show_sidebar=False)

        if user and current_app.check_password(user['passwordHash'], form.password.data):
            if not user.get('isActive', False):
                flash('Account not verified. Please check your email for the OTP.', 'error')
                session['username_for_otp'] = user['username']
                return redirect(url_for('auth.verify_otp'))
            
            current_app.update_last_login(user['username'])
            
            if user.get('otpSecret'):
                session['username_for_2fa_login'] = user['username']
                return redirect(url_for('auth.verify_otp'))
            else:
                access_token = create_access_token(identity=user['username'])
                refresh_token = create_refresh_token(identity=user['username'])
                
                # --- FIX: Redirect to the root route, not the dashboard directly ---
                response = make_response(redirect(url_for('main.root_route')))
                
                set_access_cookies(response, access_token)
                set_refresh_cookies(response, refresh_token)
                session.clear()
                return response
        else:
            if user: current_app.record_failed_login_attempt(user['username'])
            flash('Invalid username or password.', 'error')

    return render_template('login.html', form=form, show_sidebar=False)


@auth.route('/register', methods=['GET', 'POST'])
# ... (register function remains unchanged) ...
def register():
    form = RegistrationForm()
    if form.validate_on_submit():
        if current_app.add_user(form.username.data, form.email.data, form.password.data):
            otp = current_app.set_user_otp(form.username.data, otp_type='email')
            if otp:
                send_otp_email(form.email.data, otp)
                session['username_for_otp'] = form.username.data
                flash('Registration successful! Please check your email for the verification code.', 'success')
                return redirect(url_for('auth.verify_otp'))
            else:
                flash('Could not generate verification code. Please contact support.', 'error')
    return render_template('register.html', form=form, show_sidebar=False)


@auth.route('/verify-otp', methods=['GET', 'POST'])
def verify_otp():
    username = session.get('username_for_otp') or session.get('username_for_2fa_login')
    if not username:
        return redirect(url_for('auth.login'))

    is_2fa_login = 'username_for_2fa_login' in session
    form = OTPForm()

    if form.validate_on_submit():
        if is_2fa_login:
            otp_input = request.form.get('otp')
            if current_app.verify_user_otp(username, otp_input, otp_type='2fa'):
                access_token = create_access_token(identity=username)
                
                # --- FIX: Redirect to the root route, not the dashboard directly ---
                response = make_response(redirect(url_for('main.root_route')))
                
                set_access_cookies(response, access_token)
                session.clear()
                return response
            else:
                flash('Invalid 2FA code.', 'error')
        else:
            submitted_otp = "".join([request.form.get(f'otp{i}', '') for i in range(1, 7)])
            if current_app.verify_user_otp(username, submitted_otp, otp_type='email'):
                flash('Email verified! Please set up Two-Factor Authentication.', 'success')
                session.pop('username_for_otp')
                session['username_for_2fa_setup'] = username
                return redirect(url_for('auth.setup_2fa'))
            else:
                flash('Invalid or expired OTP.', 'error')
                
    return render_template('otp_verify.html', form=form, is_2fa_login=is_2fa_login, username_in_context=username)


@auth.route('/setup-2fa', methods=['GET', 'POST'])
# ... (setup_2fa function remains unchanged) ...
def setup_2fa():
    username = session.get('username_for_2fa_setup')
    if not username:
        return redirect(url_for('auth.login'))
        
    user = current_app.get_user_by_username(username)
    if not user or not user.get('otpSecret'):
        flash('Error setting up 2FA.', 'error')
        return redirect(url_for('main.dashboard'))

    form = OTPForm()
    if form.validate_on_submit():
        if current_app.verify_user_otp(username, request.form.get('otp'), otp_type='2fa'):
            flash('2FA successfully set up!', 'success')
            session.pop('username_for_2fa_setup')
            return redirect(url_for('auth.login'))
        else:
            flash('Invalid 2FA code.', 'error')

    totp = pyotp.TOTP(user['otpSecret'])
    uri = totp.provisioning_uri(name=user['email'], issuer_name="DecoOffice")
    img_buf = io.BytesIO()
    qrcode.make(uri, image_factory=qrcode.image.svg.SvgImage).save(img_buf)
    qr_code_svg = base64.b64encode(img_buf.getvalue()).decode('utf-8')
    
    return render_template('setup_2fa.html', form=form, otp_secret=user['otpSecret'], qr_code_svg=qr_code_svg)


@auth.route('/logout')
# ... (logout function remains unchanged) ...
def logout():
    response = make_response(redirect(url_for('auth.login')))
    unset_jwt_cookies(response)
    session.clear()
    flash('You have been logged out.', 'success')
    return response