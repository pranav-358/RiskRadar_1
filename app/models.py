from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from app import db

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='user')  # user, officer, admin
    first_name = db.Column(db.String(50))
    last_name = db.Column(db.String(50))
    phone = db.Column(db.String(20))
    aadhar_number = db.Column(db.String(12), unique=True)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    
    # Relationships
    claims = db.relationship('Claim', backref='claimant', lazy=True)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def is_admin(self):
        return self.role == 'admin'
    
    def is_processing_officer(self):
        return self.role in ['officer', 'admin']
    
    def __repr__(self):
        return f'<User {self.username}>'

class Claim(db.Model):
    __tablename__ = 'claims'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    policy_number = db.Column(db.String(50), nullable=False)
    policy_type = db.Column(db.String(50))
    policy_start_date = db.Column(db.DateTime)
    claim_type = db.Column(db.String(50), nullable=False)  # auto, health, property, life
    amount = db.Column(db.Float, nullable=False)
    incident_date = db.Column(db.DateTime, nullable=False)
    submission_date = db.Column(db.DateTime, default=datetime.utcnow)
    incident_location = db.Column(db.String(200))
    description = db.Column(db.Text)
    status = db.Column(db.String(20), default='submitted')  # submitted, under_review, analyzed, approved, rejected
    fraud_score = db.Column(db.Float)  # 0-100 fraud probability
    assigned_officer_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    analysis_date = db.Column(db.DateTime)
    decision_date = db.Column(db.DateTime)
    decision = db.Column(db.String(20))  # approved, rejected, pending
    decision_reason = db.Column(db.Text)
    
    # Relationships
    documents = db.relationship('Document', backref='claim', lazy=True)
    analysis_results = db.relationship('AnalysisResult', backref='claim', uselist=False)
    assigned_officer = db.relationship('User', foreign_keys=[assigned_officer_id])
    
    def __repr__(self):
        return f'<Claim {self.id} - {self.claim_type}>'

class Document(db.Model):
    __tablename__ = 'documents'
    
    id = db.Column(db.Integer, primary_key=True)
    claim_id = db.Column(db.Integer, db.ForeignKey('claims.id'), nullable=False)
    document_type = db.Column(db.String(50), nullable=False)  # prescription, bill, id_proof, etc.
    original_filename = db.Column(db.String(255), nullable=False)
    file_path = db.Column(db.String(500), nullable=False)
    file_size = db.Column(db.Integer)
    mime_type = db.Column(db.String(100))
    upload_date = db.Column(db.DateTime, default=datetime.utcnow)
    authenticity_score = db.Column(db.Float)  # 0-100 document authenticity
    is_tampered = db.Column(db.Boolean, default=False)
    analysis_results = db.Column(db.Text)  # JSON results from document verification
    analysis_date = db.Column(db.DateTime)
    
    def __repr__(self):
        return f'<Document {self.original_filename}>'

class AnalysisResult(db.Model):
    __tablename__ = 'analysis_results'
    
    id = db.Column(db.Integer, primary_key=True)
    claim_id = db.Column(db.Integer, db.ForeignKey('claims.id'), nullable=False, unique=True)
    document_verification_results = db.Column(db.Text)  # JSON
    behavioral_analysis_results = db.Column(db.Text)    # JSON
    hidden_link_results = db.Column(db.Text)           # JSON
    predictive_scoring_results = db.Column(db.Text)    # JSON
    explainable_ai_results = db.Column(db.Text)        # JSON
    overall_score = db.Column(db.Float)                # 0-100
    analysis_date = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<AnalysisResult for Claim {self.claim_id}>'

class AuditLog(db.Model):
    __tablename__ = 'audit_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    action = db.Column(db.String(100), nullable=False)  # login, claim_submission, decision, etc.
    resource_type = db.Column(db.String(50))           # claim, user, document, etc.
    resource_id = db.Column(db.Integer)                # ID of the affected resource
    details = db.Column(db.Text)                       # JSON details of the action
    ip_address = db.Column(db.String(45))
    user_agent = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationship
    user = db.relationship('User', backref='audit_logs')
    
    def __repr__(self):
        return f'<AuditLog {self.action} by User {self.user_id}>'

class SystemConfig(db.Model):
    __tablename__ = 'system_config'
    
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(100), unique=True, nullable=False)
    value = db.Column(db.Text)
    description = db.Column(db.Text)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<SystemConfig {self.key}>'
