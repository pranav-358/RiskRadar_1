# app/models/document.py

from app import db
from datetime import datetime

class Document(db.Model):
    __tablename__ = 'documents'
    
    id = db.Column(db.Integer, primary_key=True)
    claim_id = db.Column(db.Integer, db.ForeignKey('claims.id'), nullable=False)
    document_type = db.Column(db.String(50), nullable=False)
    original_filename = db.Column(db.String(255), nullable=False)
    file_path = db.Column(db.String(500), nullable=False)
    file_size = db.Column(db.Integer)
    mime_type = db.Column(db.String(100))
    upload_date = db.Column(db.DateTime, default=datetime.utcnow)
    authenticity_score = db.Column(db.Float)
    is_tampered = db.Column(db.Boolean, default=False)
    analysis_results = db.Column(db.Text)
    analysis_date = db.Column(db.DateTime)
    
    def __repr__(self):
        return f'<Document {self.original_filename}>'
