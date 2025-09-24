# website/forms.py

from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, DecimalField, SelectField, DateTimeLocalField
from wtforms.validators import DataRequired, Length, Email, EqualTo, ValidationError
from flask import current_app

class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=3, max=20)])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=8)])
    submit = SubmitField('Login')

class OTPForm(FlaskForm):
    # Primarily for CSRF in OTP/2FA forms
    submit = SubmitField('Verify')

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

class TransactionForm(FlaskForm):
    # --- THIS IS THE FIX ---
    # Expanded the form to include all fields from the template
    name = StringField('Name', validators=[DataRequired(), Length(max=100)])
    date_time = DateTimeLocalField('Delivery Date', format='%Y-%m-%dT%H:%M', validators=[DataRequired()])
    transaction_id = StringField('Check Date', validators=[DataRequired(), Length(max=50)]) # Renamed from Check No. to match label
    amount = DecimalField('Amount', validators=[DataRequired()])
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
    submit = SubmitField('Add')