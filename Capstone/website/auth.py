# website/auth.py

from flask import Blueprint, render_template, request, redirect, url_for, session, flash, make_response, current_app, jsonify
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity, set_access_cookies, unset_jwt_cookies
from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadTimeSignature
from datetime import datetime
import pyotp
import qrcode
import qrcode.image.svg
import io
import base64
import logging
import os

from . import jwt, limiter
from .forms import LoginForm, RegistrationForm, OTPForm, ForgotPasswordForm, ResetPasswordForm
from .models import get_user_by_email, update_user_password
from .utils.email_utils import send_email_via_api, send_notification_email

logger = logging.getLogger(__name__)
auth = Blueprint('auth', __name__)

def get_serializer():
    return URLSafeTimedSerializer(current_app.config['SECRET_KEY'])

# --- JWT Error Handlers (No Changes) ---
@jwt.unauthorized_loader
def unauthorized_response(callback):
    if request.path.startswith('/api/'):
        return jsonify(msg="Missing Authorization Header"), 401
    flash('Please log in to access this page.', 'error')
    return redirect(url_for('auth.login'))

@jwt.invalid_token_loader
def invalid_token_response(callback):
    if request.path.startswith('/api/'):
        return jsonify(msg="Your session is invalid. Please log in again."), 401
    flash('Your session has expired or is invalid. Please log in again.', 'error')
    return redirect(url_for('auth.login'))

@jwt.expired_token_loader
def expired_token_response(jwt_header, jwt_payload):
    if request.path.startswith('/api/'):
        return jsonify(msg="Your session has expired. Please log in again."), 401
    flash('Your session has expired. Please log in again.', 'error')
    return redirect(url_for('auth.login'))

# --- Helper Functions (MODIFIED to use API) ---
def send_otp_email(recipient_email, otp):
    """Sends OTP email using the Brevo API."""
    try:
        subject = "Your DecoOffice Verification Code"
        html_content = f"Your one-time password (OTP) is: <h2><strong>{otp}</strong></h2>"
        if send_email_via_api(recipient_email, subject, html_content):
            flash('A new OTP has been sent to your email address.', 'success')
        else:
            flash('Failed to send OTP email.', 'error')
    except Exception as e:
        logger.error(f"Failed to trigger OTP email for {recipient_email}: {e}")
        flash('Failed to send OTP email.', 'error')

def send_password_reset_email(recipient_email, token):
    """Sends password reset email using the Brevo API."""
    render_url = os.environ.get('RENDER_EXTERNAL_URL', None)
    base_url = render_url or url_for('main.root_route', _external=True)
    reset_url = f"{base_url.rstrip('/')}{url_for('auth.reset_password', token=token)}"
    
    try:
        subject = "Reset Your DecoOffice Password"
        html_content = f"<p>Please click the link to reset your password: <a href='{reset_url}'>{reset_url}</a></p>"
        send_email_via_api(recipient_email, subject, html_content)
    except Exception as e:
        logger.error(f"Failed to send password reset email to {recipient_email}: {e}")

# --- Authentication Routes (No functional changes) ---
@auth.route('/login', methods=['GET', 'POST'])
@limiter.limit("5 per minute")
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = current_app.get_user_by_username(form.username.data)
        if user and user.get('lockoutUntil') and user['lockoutUntil'] > datetime.utcnow():
            flash(f'Account locked. Try again later.', 'error')
            return render_template('login.html', form=form, show_sidebar=False)

        if user and current_app.check_password(user['passwordHash'], form.password.data):
            if not user.get('isActive', False):
                session['username_for_otp'] = user['username']
                return redirect(url_for('auth.verify_otp'))
            
            current_app.update_last_login(user['username'])
            
            if user.get('otpSecret'):
                session['username_for_2fa_login'] = user['username']
                return redirect(url_for('auth.verify_otp'))
            
            current_app.log_user_activity(user['username'], 'User Log In')
            
            access_token = create_access_token(identity=user['username'])
            response = make_response(redirect(url_for('main.root_route')))
            set_access_cookies(response, access_token)
            return response
        else:
            if user: current_app.record_failed_login_attempt(user['username'])
            flash('Invalid username or password.', 'error')
    return render_template('login.html', form=form, show_sidebar=False)

@auth.route('/register', methods=['GET', 'POST'])
def register():
    form = RegistrationForm()
    if form.validate_on_submit():
        user_added_successfully = current_app.add_user(form.username.data, form.email.data, form.password.data)
        if user_added_successfully:
            otp = current_app.set_user_otp(form.username.data, otp_type='email')
            if otp:
                send_otp_email(form.email.data, otp)
                session['username_for_otp'] = form.username.data
                return redirect(url_for('auth.verify_otp'))
        else:
            flash('Username or email already exists.', 'error')
    return render_template('register.html', form=form, show_sidebar=False)

@auth.route('/verify-otp', methods=['GET', 'POST'])
def verify_otp():
    username = session.get('username_for_otp') or session.get('username_for_2fa_login')
    if not username: return redirect(url_for('auth.login'))

    is_2fa_login = 'username_for_2fa_login' in session
    form = OTPForm()

    if form.validate_on_submit():
        otp_input = request.form.get('otp') or "".join([request.form.get(f'otp{i+1}', '') for i in range(6)])
        
        if is_2fa_login:
            if current_app.verify_user_otp(username, otp_input, otp_type='2fa'):
                
                current_app.log_user_activity(username, 'User Log In')

                access_token = create_access_token(identity=username)
                response = make_response(redirect(url_for('main.root_route')))
                set_access_cookies(response, access_token)
                session.clear()
                return response
            else:
                flash('Invalid 2FA code.', 'error')
        else:
            if current_app.verify_user_otp(username, otp_input, otp_type='email'):
                session.pop('username_for_otp')
                session['username_for_2fa_setup'] = username
                return redirect(url_for('auth.setup_2fa'))
            else:
                flash('Invalid or expired OTP.', 'error')
            
    return render_template('otp_verify.html', form=form, is_2fa_login=is_2fa_login, username_in_context=username)

@auth.route('/setup-2fa', methods=['GET', 'POST'])
def setup_2fa():
    username = session.get('username_for_2fa_setup')
    if not username: return redirect(url_for('auth.login'))
        
    user = current_app.get_user_by_username(username)
    if not user: return redirect(url_for('auth.login'))

    form = OTPForm()
    if form.validate_on_submit():
        if current_app.verify_user_otp(username, request.form.get('otp'), otp_type='2fa'):
            flash('2FA successfully set up! Please log in.', 'success')
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
def logout():
    response = make_response(redirect(url_for('auth.login')))
    unset_jwt_cookies(response)
    session.clear()
    return response

@auth.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    form = ForgotPasswordForm()
    if form.validate_on_submit():
        user = get_user_by_email(form.email.data)
        if user:
            s = get_serializer()
            token = s.dumps(form.email.data, salt='password-reset-salt')
            send_password_reset_email(form.email.data, token)
        flash('If your email is in our system, a reset link has been sent.', 'success')
        return redirect(url_for('auth.login'))
    return render_template('forgot_password.html', form=form)

@auth.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    s = get_serializer()
    try:
        email = s.loads(token, salt='password-reset-salt', max_age=1800)
    except (SignatureExpired, BadTimeSignature):
        flash('The password reset link is invalid or has expired.', 'error')
        return redirect(url_for('auth.forgot_password'))

    form = ResetPasswordForm()
    if form.validate_on_submit():
        if update_user_password(email, form.password.data):
            flash('Your password has been updated! You can now log in.', 'success')
            return redirect(url_for('auth.login'))
        else:
            flash('An error occurred. Please try again.', 'error')
    return render_template('reset_password.html', form=form, token=token)