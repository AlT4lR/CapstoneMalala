# website/auth.py

from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from flask_mail import Message
from . import get_mail # FIX: Import get_mail
from .models import get_user_by_username, add_user, check_password, update_last_login, set_user_otp, verify_user_otp
import re

auth = Blueprint('auth', __name__)

def send_otp_email(recipient_email, otp):
    """Sends the OTP code to the user's email."""
    # FIX: Use get_mail() to ensure the mail instance is correctly retrieved
    mail = get_mail()
    if not mail:
        print("[ERROR] Mail extension is not initialized. Cannot send email.")
        flash('Could not send OTP email due to a server configuration error.', 'error')
        return

    try:
        msg = Message(
            subject="Your DecoOffice Verification Code",
            recipients=[recipient_email],
            body=f"Welcome to DecoOffice!\n\nYour one-time password (OTP) is: {otp}\n\nThis code will expire in 10 minutes. Please do not share it with anyone.\n\nIf you did not request this, please ignore this email.\n\nBest regards,\nThe DecoOffice Team"
        )
        mail.send(msg)
        print(f"Successfully sent OTP to {recipient_email}")
        flash('A new OTP has been sent to your email address.', 'success')
    except Exception as e:
        print(f"[ERROR] Failed to send email to {recipient_email}: {e}")
        flash('Failed to send OTP email. Please try again later.', 'error')


@auth.route('/login', methods=['GET'])
def login():
    if 'username' in session:
        return redirect(url_for('main.branches'))
    return render_template('login.html')

@auth.route('/login', methods=['POST'])
def login_post():
    username = request.form.get('username')
    password = request.form.get('password')

    user = get_user_by_username(username)

    if not user:
        flash('Invalid username or password.', 'error')
        return redirect(url_for('auth.login'))

    if not user.get('isActive', False):
        flash('Your account is not verified. Please check your email for the OTP.', 'error')
        session['username_for_otp'] = user['username']
        return redirect(url_for('auth.verify_otp'))

    if user and check_password(user['passwordHash'], password):
        session.clear()
        session['username'] = user['username']
        update_last_login(user['username'])
        flash('Login successful!', 'success')
        return redirect(url_for('main.branches'))
    else:
        flash('Invalid username or password.', 'error')
        return redirect(url_for('auth.login'))

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

    if len(password) < 8 or \
       not re.search(r"[a-z]", password) or \
       not re.search(r"[A-Z]", password) or \
       not re.search(r"[0-9]", password) or \
       not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
        flash('Password must be at least 8 characters long and contain at least one uppercase letter, one lowercase letter, one number, and one special character.', 'error')
        return render_template('register.html', username=username, email=email)

    if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
        flash('Invalid email address.', 'error')
        return render_template('register.html', username=username)

    user_added = add_user(username, email, password)

    if user_added:
        otp_generated = set_user_otp(username)
        if otp_generated:
            send_otp_email(email, otp_generated)  # Send the OTP via email
            session['username_for_otp'] = username
            return redirect(url_for('auth.verify_otp'))
        else:
            flash('Could not generate OTP. Please contact support.', 'error')
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

    if request.method == 'POST':
        otp_list = [request.form.get(f'otp{i}') for i in range(1, 7)]
        if not all(otp_list):
            flash('Please enter the complete 6-digit OTP.', 'error')
            return redirect(url_for('auth.verify_otp'))

        submitted_otp = "".join(otp_list)

        if verify_user_otp(username_for_otp, submitted_otp):
            flash('Email verified successfully! You can now log in.', 'success')
            session.pop('username_for_otp', None)
            return redirect(url_for('auth.login'))
        else:
            flash('Invalid or expired OTP. Please try again.', 'error')
            return redirect(url_for('auth.verify_otp'))

    return render_template('otp_verify.html')

@auth.route('/resend-otp')
def resend_otp():
    username = session.get('username_for_otp')
    if not username:
        flash('No user session found. Please log in.', 'error')
        return redirect(url_for('auth.login'))

    user = get_user_by_username(username)
    if not user:
        flash('An error occurred. User not found.', 'error')
        return redirect(url_for('auth.login'))

    otp_generated = set_user_otp(username)
    if otp_generated:
        send_otp_email(user['email'], otp_generated) # Re-send the email
    else:
        flash('Could not generate a new OTP. Please try again later.', 'error')

    return redirect(url_for('auth.verify_otp'))


@auth.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'success')
    return redirect(url_for('auth.login'))