# website/forms.py

from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, DecimalField, DateField
from wtforms.validators import DataRequired, Length, Email, EqualTo, Optional, ValidationError
from flask import current_app
import re

class LoginForm(FlaskForm):
    """Form for user login."""
    username = StringField('Username', validators=[DataRequired(), Length(min=2, max=20)])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')

class RegistrationForm(FlaskForm):
    """Form for user registration."""
    username = StringField('Username', validators=[DataRequired(), Length(min=2, max=20)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=8)])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Sign Up')

    def validate_username(self, username):
        if current_app.get_user_by_username(username.data):
            raise ValidationError('That username is already taken.')

    def validate_email(self, email):
        if current_app.get_user_by_email(email.data):
            raise ValidationError('That email is already registered.')

class OTPForm(FlaskForm):
    """Form for OTP and 2FA verification."""
    submit = SubmitField('Verify')

class ForgotPasswordForm(FlaskForm):
    """Form for requesting a password reset link."""
    email = StringField('Email', validators=[DataRequired(), Email()])
    submit = SubmitField('Send Reset Link')

class ResetPasswordForm(FlaskForm):
    """Form for setting a new password after a reset request."""
    password = PasswordField('New Password', validators=[DataRequired(), Length(min=8)])
    confirm_password = PasswordField('Confirm New Password', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Reset Password')

class TransactionForm(FlaskForm):
    """Form for the 'Create Issued Checked' modal."""
    name_of_issued_check = StringField('Name Of Issued Checked', validators=[DataRequired(), Length(max=100)])
    # --- START OF MODIFICATION: Make check_no optional for the initial folder creation ---
    check_no = StringField('Check No.', validators=[Optional(), Length(max=50)])
    # --- END OF MODIFICATION ---
    check_date = DateField('Check Date', format='%Y-%m-%d', validators=[DataRequired()])
    countered_check = DecimalField('Countered Check', validators=[Optional()])
    ewt = DecimalField('EWT', validators=[Optional()])
    submit = SubmitField('Add')

class LoanForm(FlaskForm):
    """Form for the 'Create Loan' modal."""
    name_of_loan = StringField('Name Of Loans', validators=[DataRequired(), Length(max=100)])
    bank_name = StringField('Bank Name', validators=[DataRequired(), Length(max=100)])
    amount = DecimalField('Amount', validators=[DataRequired()])
    date_issued = DateField('Date Issued', format='%Y-%m-%d', validators=[DataRequired()])
    date_paid = DateField('Date Paid', format='%Y-%m-%d', validators=[Optional()])
    submit = SubmitField('Add')