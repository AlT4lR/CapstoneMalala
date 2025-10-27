# website/forms.py
from flask_wtf import FlaskForm
from wtforms import (
    StringField, PasswordField, SubmitField,
    DecimalField, DateField, TextAreaField
)
from wtforms.validators import (
    DataRequired, Length, Email, EqualTo,
    Optional, ValidationError
)
from flask import current_app
import re

# --- Custom Password Validator ---
def password_complexity(form, field):
    password = field.data
    errors = []
    if not re.search(r'[A-Z]', password):
        errors.append("One upper character")
    if not re.search(r'[a-z]', password):
        errors.append("One lowercase character")
    if not re.search(r'[0-9]', password):
        errors.append("One number")
    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        errors.append("One special character")
    if errors:
        raise ValidationError(f"Password must contain: {', '.join(errors)}.")


# -------------------------
# AUTHENTICATION FORMS
# -------------------------

class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=2, max=20)])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')


class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=2, max=20)])
    name = StringField('Name', validators=[DataRequired(), Length(min=2, max=50)]) # Added name field
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
    submit = SubmitField('Verify')


class ForgotPasswordForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    submit = SubmitField('Send Reset Link')


class ResetPasswordForm(FlaskForm):
    password = PasswordField('New Password', validators=[DataRequired(), Length(min=8)])
    confirm_password = PasswordField('Confirm New Password', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Reset Password')


# --- START OF NEW FORMS ---

class UpdatePersonalInfoForm(FlaskForm):
    """Form for updating user's personal information."""
    name = StringField('Name', validators=[DataRequired(), Length(max=50)])
    submit = SubmitField('Save')

class ChangePasswordForm(FlaskForm):
    """Form for changing the user's password."""
    old_password = PasswordField('Old Password', validators=[DataRequired()])
    new_password = PasswordField('New Password', validators=[DataRequired(), Length(min=12), password_complexity])
    confirm_new_password = PasswordField('Confirm New Password', validators=[DataRequired(), EqualTo('new_password', message='New passwords must match.')])
    submit = SubmitField('Change Password')

# --- END OF NEW FORMS ---

# -------------------------
# BILLINGS / TRANSACTIONS FORMS
# -------------------------

class TransactionForm(FlaskForm):
    """Form for creating transactions (both folders and issued checks)."""
    name_of_issued_check = StringField('Name Of Issued Checked', validators=[DataRequired(), Length(max=100)])
    check_no = StringField('Check No.', validators=[Optional(), Length(max=50)])
    check_date = DateField('Date Created', format='%Y-%m-%d', validators=[DataRequired()])
    # --- START OF MODIFICATION ---
    due_date = DateField('Due Date', format='%Y-%m-%d', validators=[Optional()])
    # --- END OF MODIFICATION ---
    countered_check = DecimalField('Countered Check', validators=[Optional()])
    ewt = DecimalField('EWT', validators=[Optional()])
    submit = SubmitField('Add')


class EditTransactionForm(FlaskForm):
    """Form for editing a transaction."""
    name = StringField('Recipient Name', validators=[DataRequired(), Length(max=100)])
    check_date = DateField('Check Date', format='%Y-%m-%d', validators=[DataRequired()])
    due_date = DateField('Due Date', format='%Y-%m-%d', validators=[Optional()])
    ewt = DecimalField('EWT', validators=[Optional()])
    countered_check = DecimalField('Countered Check', validators=[Optional()])
    notes = TextAreaField('Notes', validators=[Optional(), Length(max=1000)])
    submit = SubmitField('Save Changes')


# -------------------------
# LOAN FORMS
# -------------------------

class LoanForm(FlaskForm):
    """Form for the 'Create Loan' modal."""
    name_of_loan = StringField('Name Of Loans', validators=[DataRequired(), Length(max=100)])
    bank_name = StringField('Bank Name', validators=[DataRequired(), Length(max=100)])
    amount = DecimalField('Amount', validators=[DataRequired()])
    date_issued = DateField('Date Issued', format='%Y-%m-%d', validators=[DataRequired()])
    date_paid = DateField('Date Paid', format='%Y-%m-%d', validators=[Optional()])
    submit = SubmitField('Add')