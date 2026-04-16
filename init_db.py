"""
Database initialization script for RiskRadar
This script creates all database tables and optionally creates a default admin user
"""
import os
os.environ['SKIP_AI_INIT'] = '1'  # Skip AI model loading during DB init

from app import create_app, db
from app.models import User
from datetime import datetime

def init_database():
    """Initialize the database with all tables"""
    app = create_app()
    
    with app.app_context():
        print("Creating database tables...")
        db.create_all()
        print("✓ Database tables created successfully!")
        
        # Check if any users exist
        user_count = User.query.count()
        
        if user_count == 0:
            print("\nNo users found. Creating default users...")
            
            # Create admin user
            admin = User(
                username='admin',
                email='admin@riskradar.com',
                first_name='Admin',
                last_name='User',
                phone='1234567890',
                aadhar_number='123456789012',
                role='admin',
                is_active=True,
                created_at=datetime.utcnow()
            )
            admin.set_password('admin123')
            db.session.add(admin)
            
            # Create officer user
            officer = User(
                username='officer',
                email='officer@riskradar.com',
                first_name='Officer',
                last_name='User',
                phone='9876543210',
                aadhar_number='987654321098',
                role='officer',
                is_active=True,
                created_at=datetime.utcnow()
            )
            officer.set_password('officer123')
            db.session.add(officer)
            
            # Create regular user
            user = User(
                username='user',
                email='user@riskradar.com',
                first_name='Regular',
                last_name='User',
                phone='5555555555',
                aadhar_number='555555555555',
                role='user',
                is_active=True,
                created_at=datetime.utcnow()
            )
            user.set_password('user123')
            db.session.add(user)
            
            db.session.commit()
            
            print("✓ Default users created successfully!")
            print("\nDefault Login Credentials:")
            print("=" * 50)
            print("Admin:   username='admin'   password='admin123'")
            print("Officer: username='officer' password='officer123'")
            print("User:    username='user'    password='user123'")
            print("=" * 50)
        else:
            print(f"\n✓ Database already has {user_count} user(s)")
        
        print("\n✓ Database initialization complete!")
        print(f"Database location: {app.config['SQLALCHEMY_DATABASE_URI']}")

if __name__ == '__main__':
    init_database()
