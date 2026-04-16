from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, TextAreaField, SelectField, \
    DateField, DecimalField, FileField, BooleanField
from wtforms.validators import DataRequired, Email, Length, EqualTo, Optional, \
    NumberRange, ValidationError
from app.models import User
import re

class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=3, max=80)])
    password = PasswordField('Password', validators=[DataRequired()])
    remember_me = BooleanField('Remember Me')

class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=3, max=80)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[
        DataRequired(), 
        Length(min=8),
        EqualTo('confirm_password', message='Passwords must match')
    ])
    confirm_password = PasswordField('Confirm Password')
    first_name = StringField('First Name', validators=[DataRequired(), Length(max=50)])
    last_name = StringField('Last Name', validators=[DataRequired(), Length(max=50)])
    phone = StringField('Phone Number', validators=[DataRequired(), Length(min=10, max=15)])
    aadhar_number = StringField('Aadhar Number', validators=[DataRequired(), Length(min=12, max=12)])
    
    def validate_username(self, field):
        if User.query.filter_by(username=field.data).first():
            raise ValidationError('Username already exists.')
    
    def validate_email(self, field):
        if User.query.filter_by(email=field.data).first():
            raise ValidationError('Email already exists.')
    
    def validate_aadhar_number(self, field):
        if not field.data.isdigit():
            raise ValidationError('Aadhar number must contain only digits.')
        if User.query.filter_by(aadhar_number=field.data).first():
            raise ValidationError('Aadhar number already registered.')

class ClaimForm(FlaskForm):
    policy_number = StringField('Policy Number', validators=[DataRequired(), Length(max=50)])
    policy_type = SelectField('Policy Type', choices=[
        ('', 'Select Policy Type'),
        ('comprehensive', 'Comprehensive'),
        ('basic', 'Basic'),
        ('premium', 'Premium')
    ], validators=[DataRequired()])
    claim_type = SelectField('Claim Type', choices=[
        ('', 'Select Claim Type'),
        ('auto', 'Auto Insurance'),
        ('health', 'Health Insurance'),
        ('property', 'Property Insurance'),
        ('life', 'Life Insurance')
    ], validators=[DataRequired()])
    amount = DecimalField('Claim Amount', validators=[DataRequired(), NumberRange(min=0)])
    incident_date = DateField('Incident Date', validators=[DataRequired()])
    incident_location = StringField('Incident Location', validators=[DataRequired(), Length(max=200)])
    description = TextAreaField('Description', validators=[DataRequired(), Length(max=1000)])
    document_type = SelectField('Document Type', choices=[
        ('', 'Select Document Type'),
        ('prescription', 'Medical Prescription'),
        ('bill', 'Medical Bill'),
        ('id_proof', 'ID Proof'),
        ('fir', 'FIR Copy'),
        ('estimate', 'Repair Estimate'),
        ('photos', 'Damage Photos'),
        ('other', 'Other')
    ], validators=[Optional()])
    file = FileField('Document Files', validators=[Optional()])

class DocumentUploadForm(FlaskForm):
    document_type = SelectField('Document Type', choices=[
        ('', 'Select Document Type'),
        ('prescription', 'Medical Prescription'),
        ('bill', 'Medical Bill'),
        ('id_proof', 'ID Proof'),
        ('fir', 'FIR Copy'),
        ('estimate', 'Repair Estimate'),
        ('photos', 'Damage Photos'),
        ('other', 'Other')
    ], validators=[DataRequired()])
    file = FileField('Document File', validators=[DataRequired()])

class UserProfileForm(FlaskForm):
    first_name = StringField('First Name', validators=[DataRequired(), Length(max=50)])
    last_name = StringField('Last Name', validators=[DataRequired(), Length(max=50)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    phone = StringField('Phone Number', validators=[DataRequired(), Length(min=10, max=15)])
    
    def validate_email(self, field):
        # Check if email exists for another user
        user = User.query.filter_by(email=field.data).first()
        if user and user.id != self.user_id:
            raise ValidationError('Email already exists.')

class PasswordChangeForm(FlaskForm):
    current_password = PasswordField('Current Password', validators=[DataRequired()])
    new_password = PasswordField('New Password', validators=[
        DataRequired(), 
        Length(min=8),
        EqualTo('confirm_password', message='Passwords must match')
    ])
    confirm_password = PasswordField('Confirm New Password')

class AdminUserForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=3, max=80)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    first_name = StringField('First Name', validators=[DataRequired(), Length(max=50)])
    last_name = StringField('Last Name', validators=[DataRequired(), Length(max=50)])
    phone = StringField('Phone Number', validators=[Optional(), Length(min=10, max=15)])
    role = SelectField('Role', choices=[
        ('user', 'User'),
        ('officer', 'Processing Officer'),
        ('admin', 'Administrator')
    ], validators=[DataRequired()])
    is_active = BooleanField('Active', default=True)

class ClaimDecisionForm(FlaskForm):
    decision = SelectField('Decision', choices=[
        ('approved', 'Approve Claim'),
        ('rejected', 'Reject Claim'),
        ('pending', 'Need More Information')
    ], validators=[DataRequired()])
    reason = TextAreaField('Reason', validators=[DataRequired(), Length(max=1000)])

class SystemConfigForm(FlaskForm):
    fraud_threshold_high = DecimalField('High Risk Threshold', validators=[DataRequired(), NumberRange(min=0, max=100)])
    fraud_threshold_medium = DecimalField('Medium Risk Threshold', validators=[DataRequired(), NumberRange(min=0, max=100)])
    auto_assign_officers = BooleanField('Auto-Assign Claims to Officers')
    max_file_size = DecimalField('Maximum File Size (MB)', validators=[DataRequired(), NumberRange(min=1, max=50)])
