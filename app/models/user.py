# app/models/user.py

from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from app import db

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='user')
    first_name = db.Column(db.String(50))
    last_name = db.Column(db.String(50))
    phone = db.Column(db.String(20))
    aadhar_number = db.Column(db.String(12), unique=True)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=db.func.now())
    last_login = db.Column(db.DateTime)
    
    # Relationships
    claims = db.relationship('Claim', foreign_keys='Claim.user_id', backref='user', lazy=True)
    
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
