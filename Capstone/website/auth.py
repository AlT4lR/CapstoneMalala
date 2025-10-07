from flask import Blueprint, render_template, request, redirect, url_for, session, flash, make_response, current_app
from flask_mail import Message
from flask_jwt_extended import create_access_token, create_refresh_token, jwt_required, get_jwt_identity, set_access_cookies, set_refresh_cookies, unset_jwt_cookies
# Imports for password reset token serialization and handling
from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadTimeSignature
from datetime import datetime
import pyotp
import qrcode
import qrcode.image.svg
import io
import base64
import logging

from . import jwt, limiter
# Updated form imports
from .forms import LoginForm, RegistrationForm, OTPForm, ForgotPasswordForm, ResetPasswordForm
# Import the necessary model functions
from .models import get_user_by_email, update_user_password

logger = logging.getLogger(__name__)
auth = Blueprint('auth', __name__)

# --- Serializer for Password Reset Token ---
def get_serializer():
    """Initializes and returns a URLSafeTimedSerializer."""
    return URLSafeTimedSerializer(current_app.config['SECRET_KEY'])

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
    try:
        msg = Message("Your DecoOffice Verification Code", recipients=[recipient_email])
        msg.body = f"Welcome to DecoOffice!\n\nYour one-time password (OTP) is: {otp}\n\nThis code will expire in 10 minutes."
        current_app.mail.send(msg)
        logger.info(f"Successfully sent OTP to {recipient_email}")
        flash('A new OTP has been sent to your email address.', 'success')
    except Exception as e:
        logger.error(f"Failed to send email to {recipient_email}: {e}")
        flash('Failed to send OTP email. Please try again later.', 'error')

def send_password_reset_email(recipient_email, token):
    """Sends the password reset link to the user's email."""
    reset_url = url_for('auth.reset_password', token=token, _external=True)
    try:
        msg = Message("Reset Your DecoOffice Password", recipients=[recipient_email])
        msg.body = f"Hello,\n\nPlease click the link below to reset your password:\n\n{reset_url}\n\nThis link will expire in 30 minutes."
        current_app.mail.send(msg)
        logger.info(f"Successfully sent password reset email to {recipient_email}")
    except Exception as e:
        logger.error(f"Failed to send password reset email to {recipient_email}: {e}")
        pass 

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
            
            if user.get('otpSecret'): # If 2FA is enabled
                session['username_for_2fa_login'] = user['username']
                # Redirect to the 2FA verification page, which is also verify_otp
                return redirect(url_for('auth.verify_otp'))
            else: # If 2FA is not enabled
                access_token = create_access_token(identity=user['username'])
                refresh_token = create_refresh_token(identity=user['username'])
                
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
        # Combine the 6 OTP fields for email verification
        submitted_otp = "".join([request.form.get(f'otp{i+1}', '') for i in range(6)])
        # For 2FA, the single field is named 'otp'
        if is_2fa_login:
            submitted_otp = request.form.get('otp')

        otp_type = '2fa' if is_2fa_login else 'email'
        
        if current_app.verify_user_otp(username, submitted_otp, otp_type=otp_type):
            if is_2fa_login:
                access_token = create_access_token(identity=username)
                response = make_response(redirect(url_for('main.root_route')))
                set_access_cookies(response, access_token)
                session.clear()
                return response
            else: # Email verification success
                flash('Email verified! Please set up Two-Factor Authentication.', 'success')
                session.pop('username_for_otp')
                session['username_for_2fa_setup'] = username
                return redirect(url_for('auth.setup_2fa'))
        else:
            flash('Invalid or expired code.', 'error')
            
    return render_template('otp_verify.html', form=form, is_2fa_login=is_2fa_login, username_in_context=username)


@auth.route('/setup-2fa', methods=['GET', 'POST'])
def setup_2fa():
    username = session.get('username_for_2fa_setup')
    if not username:
        return redirect(url_for('auth.login'))
        
    user = current_app.get_user_by_username(username)
    if not user or not user.get('otpSecret'):
        flash('Error setting up 2FA.', 'error')
        return redirect(url_for('auth.login'))

    form = OTPForm()
    if form.validate_on_submit():
        if current_app.verify_user_otp(username, request.form.get('otp'), otp_type='2fa'):
            flash('2FA successfully set up! Please log in to continue.', 'success')
            session.pop('username_for_2fa_setup')
            return redirect(url_for('auth.login'))
        else:
            flash('Invalid 2FA code. Please try again.', 'error')

    # Generate QR code for setup
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
    flash('You have been logged out.', 'success')
    return response

@auth.route('/resend_otp')
def resend_otp():
    username = session.get('username_for_otp')
    if not username:
        flash('Session expired. Please try logging in again.', 'error')
        return redirect(url_for('auth.login'))
    
    user = current_app.get_user_by_username(username)
    if not user:
        flash('User not found.', 'error')
        return redirect(url_for('auth.login'))

    otp = current_app.set_user_otp(username, otp_type='email')
    if otp:
        send_otp_email(user['email'], otp)
    else:
        flash('Failed to generate a new OTP.', 'error')
        
    return redirect(url_for('auth.verify_otp'))

# --- Password Reset: Request Email ---
@auth.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    form = ForgotPasswordForm()
    if form.validate_on_submit():
        email = form.email.data
        user = get_user_by_email(email)
        
        if user:
            s = get_serializer()
            token = s.dumps(email, salt='password-reset-salt')
            send_password_reset_email(email, token)
            
        # Generic success message to prevent email enumeration
        flash('If an account with that email exists, a password reset link has been sent.', 'success')
        return redirect(url_for('auth.login'))
        
    return render_template('forgot_password.html', form=form)

# --- Password Reset: Reset Password ---
@auth.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    s = get_serializer()
    email = None
    try:
        # Verify the token (max_age=1800 seconds / 30 minutes)
        email = s.loads(token, salt='password-reset-salt', max_age=1800)
    except SignatureExpired:
        flash('The password reset link has expired. Please request a new one.', 'error')
        return redirect(url_for('auth.forgot_password'))
    except (BadTimeSignature, Exception) as e:
        logger.warning(f"Invalid password reset token used: {e}")
        flash('Invalid password reset link.', 'error')
        return redirect(url_for('auth.forgot_password'))

    # If the token is valid, display the form
    form = ResetPasswordForm()
    if form.validate_on_submit():
        new_password = form.password.data
        
        if update_user_password(email, new_password):
            flash('Your password has been updated! You can now log in.', 'success')
            return redirect(url_for('auth.login'))
        else:
            flash('An error occurred. Please try again.', 'error')
            
    return render_template('reset_password.html', form=form, token=token)