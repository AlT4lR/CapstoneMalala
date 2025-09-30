# website/forms.py

from flask_wtf import FlaskForm
# Make sure all field types are imported
from wtforms import StringField, PasswordField, SubmitField, DecimalField, SelectField, DateField
from wtforms.validators import DataRequired, Length, Email, EqualTo, ValidationError, Optional
from flask import current_app
import re

# --- THIS IS THE COMPLETE AND CORRECTED FILE ---

class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=3, max=20)])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=8)])
    submit = SubmitField('Login')

class OTPForm(FlaskForm):
    """A simple form primarily used for CSRF protection on OTP/2FA pages."""
    submit = SubmitField('Verify')

class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=3, max=20)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[
        DataRequired(),
        Length(min=8, message='Password must be at least 8 characters long.')
    ])
    confirm_password = PasswordField('Confirm Password', validators=[
        DataRequired(),
        EqualTo('password', message='Passwords must match.')
    ])
    submit = SubmitField('Register')

    def validate_password(self, field):
        password = field.data
        if not re.search(r'[A-Z]', password): raise ValidationError('Password must contain at least one uppercase letter.')
        if not re.search(r'[a-z]', password): raise ValidationError('Password must contain at least one lowercase letter.')
        if not re.search(r'\d', password): raise ValidationError('Password must contain at least one number.')
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password): raise ValidationError('Password must contain at least one special character.')

    def validate_username(self, username):
        if current_app.get_user_by_username(username.data):
            raise ValidationError('That username is taken. Please choose a different one.')

    def validate_email(self, email):
        if current_app.get_user_by_email(email.data):
            raise ValidationError('That email is already registered. Please use a different one.')

class ForgotPasswordForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    submit = SubmitField('Send Reset Link')

class ResetPasswordForm(FlaskForm):
    password = PasswordField('New Password', validators=[DataRequired(), Length(min=8)])
    confirm_password = PasswordField('Confirm New Password', validators=[DataRequired(), EqualTo('password', message='Passwords must match.')])
    submit = SubmitField('Reset Password')

    def validate_password(self, field):
        password = field.data
        if not re.search(r'[A-Z]', password): raise ValidationError('Password must contain at least one uppercase letter.')
        if not re.search(r'[a-z]', password): raise ValidationError('Password must contain at least one lowercase letter.')
        if not re.search(r'\d', password): raise ValidationError('Password must contain at least one number.')
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password): raise ValidationError('Password must contain at least one special character.')

class TransactionForm(FlaskForm):
    """Form for adding or editing a transaction."""
    name_of_issued_check = StringField('Names of Issued Check', validators=[DataRequired(), Length(max=100)])
    check_no = StringField('Check No.', validators=[DataRequired(), Length(max=50)])
    check_date = DateField('Check Date', format='%Y-%m-%d', validators=[DataRequired()])
    countered_check = DecimalField('Countered Check', validators=[Optional()])
    check_amount = DecimalField('Check Amount', validators=[DataRequired()])
    ewt = DecimalField('EWT', validators=[Optional()])
    payment_method = SelectField('Payment Method',
                                 choices=[
                                     ('Bank-to-Bank', 'Bank-to-Bank'),
                                     ('Cash', 'Cash'),
                                     ('Check', 'Check'),
                                     ('E-Wallet', 'E-Wallet')
                                 ], validators=[DataRequired()])
    status = SelectField('Status',
                         choices=[
                             ('Paid', 'Paid'),
                             ('Pending', 'Pending'),
                             ('Declined', 'Declined')
                         ], validators=[DataRequired()])
    submit = SubmitField('Add Transaction')