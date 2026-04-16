# app/models/claim.py

from app import db
from datetime import datetime

class Claim(db.Model):
    __tablename__ = 'claims'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    policy_number = db.Column(db.String(50), nullable=False)
    policy_type = db.Column(db.String(50))
    policy_start_date = db.Column(db.DateTime)
    claim_type = db.Column(db.String(50), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    incident_date = db.Column(db.DateTime, nullable=False)
    submission_date = db.Column(db.DateTime, default=datetime.utcnow)
    incident_location = db.Column(db.String(200))
    description = db.Column(db.Text)
    status = db.Column(db.String(20), default='submitted')
    fraud_score = db.Column(db.Float)
    assigned_officer_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    analysis_date = db.Column(db.DateTime)
    decision_date = db.Column(db.DateTime)
    decision = db.Column(db.String(20))
    decision_reason = db.Column(db.Text)
    
    # Relationships - specify foreign_keys to avoid ambiguity
    documents = db.relationship('Document', backref='claim', lazy=True)
    analysis_results = db.relationship('AnalysisResult', backref='claim', uselist=False)
    
    # Explicitly specify foreign keys for user relationships
    claimant = db.relationship('User', foreign_keys=[user_id], backref='submitted_claims', overlaps="claims,user")
    assigned_officer = db.relationship('User', foreign_keys=[assigned_officer_id], backref='assigned_claims')
    
    def __repr__(self):
        return f'<Claim {self.id} - {self.claim_type}>'
