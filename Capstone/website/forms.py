# website/forms.py

from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Length, Email, EqualTo, ValidationError
from flask import current_app

# --- Login Form ---
class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=3, max=20)])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=8)])
    # submit = SubmitField('Login') # Optional: if you want to use WTForms for the submit button

# --- OTP Form ---
# This form is primarily for CSRF protection.
# The OTP inputs are handled manually in the HTML template.
class OTPForm(FlaskForm):
    pass 

# --- Registration Form (Example, if you plan to use WTForms for registration) ---
# If you are not using WTForms for registration fields and only for CSRF,
# you can keep it simple or remove it if not needed.
class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=3, max=20)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=8)])
    # You might want to add a confirm_password field for better UX
    # confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])
    # submit = SubmitField('Register')

    def validate_username(self, username):
        # Use current_app to access the database and helper functions
        if current_app.get_user_by_username(username.data):
            raise ValidationError('That username is taken. Please choose a different one.')

    def validate_email(self, email):
        # Use current_app to access the database and helper functions
        if current_app.get_user_by_email(email.data): # Assuming get_user_by_email exists in models
            raise ValidationError('That email is already registered. Please use a different one.')