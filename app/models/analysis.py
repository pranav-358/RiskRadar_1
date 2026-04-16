# app/models/analysis.py

from app import db
from datetime import datetime

class AnalysisResult(db.Model):
    __tablename__ = 'analysis_results'
    
    id = db.Column(db.Integer, primary_key=True)
    claim_id = db.Column(db.Integer, db.ForeignKey('claims.id'), nullable=False, unique=True)
    document_verification_results = db.Column(db.Text)
    behavioral_analysis_results = db.Column(db.Text)
    hidden_link_results = db.Column(db.Text)
    predictive_scoring_results = db.Column(db.Text)
    explainable_ai_results = db.Column(db.Text)
    overall_score = db.Column(db.Float)
    analysis_date = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<AnalysisResult for Claim {self.claim_id}>'
