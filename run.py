#!/usr/bin/env python3
"""
RiskRadar - Insurance Claim Fraud Detection System
Main application runner
"""

# CRITICAL: Set matplotlib backend BEFORE any imports
import os
os.environ['MPLBACKEND'] = 'Agg'

from app import create_app, db
from app.models import User, Claim, Document, AnalysisResult, AuditLog, SystemConfig
from app.utils.helpers import generate_synthetic_training_data
import click

app = create_app()

@app.shell_context_processor
def make_shell_context():
    return {
        'db': db, 
        'User': User, 
        'Claim': Claim, 
        'Document': Document,
        'AnalysisResult': AnalysisResult,
        'AuditLog': AuditLog,
        'SystemConfig': SystemConfig
    }

@app.cli.command("init-db")
@click.option('--sample-data', is_flag=True, help='Add sample data')
def init_db(sample_data):
    """Initialize the database"""
    with app.app_context():
        # Create tables
        db.create_all()
        
        # Create default admin user
        admin_user = User.query.filter_by(username='admin').first()
        if not admin_user:
            admin_user = User(
                username='admin',
                email='admin@riskradar.com',
                first_name='System',
                last_name='Administrator',
                role='admin',
                is_active=True
            )
            admin_user.set_password('admin123')
            db.session.add(admin_user)
            db.session.commit()
            print("Created default admin user: admin / admin123")
        
        # Create default officer user
        officer_user = User.query.filter_by(username='officer').first()
        if not officer_user:
            officer_user = User(
                username='officer',
                email='officer@riskradar.com',
                first_name='Processing',
                last_name='Officer',
                role='officer',
                is_active=True
            )
            officer_user.set_password('officer123')
            db.session.add(officer_user)
            db.session.commit()
            print("Created default officer user: officer / officer123")
        
        # Create default system configuration
        default_config = {
            'fraud_threshold_high': '75',
            'fraud_threshold_medium': '50',
            'auto_assign_officers': 'True',
            'max_file_size': '16'
        }
        
        for key, value in default_config.items():
            config_item = SystemConfig.query.filter_by(key=key).first()
            if not config_item:
                config_item = SystemConfig(key=key, value=value)
                db.session.add(config_item)
        
        db.session.commit()
        print("Created default system configuration")
        
        if sample_data:
            # Generate sample training data
            sample_users = 10
            sample_claims = 50
            
            print(f"Generating {sample_users} sample users...")
            for i in range(1, sample_users + 1):
                user = User(
                    username=f'user{i}',
                    email=f'user{i}@example.com',
                    first_name=f'User{i}',
                    last_name='Test',
                    role='user',
                    is_active=True,
                    phone=f'987654321{i}',
                    aadhar_number=f'1234567890{i:02d}'
                )
                user.set_password('user123')
                db.session.add(user)
            
            db.session.commit()
            print(f"Generated {sample_users} sample users")
            
            # Generate sample claims
            print(f"Generating {sample_claims} sample claims...")
            users = User.query.filter_by(role='user').all()
            claim_types = ['auto', 'health', 'property', 'life']
            policy_types = ['comprehensive', 'basic', 'premium']
            locations = ['Mumbai', 'Delhi', 'Bangalore', 'Chennai', 'Kolkata']
            
            from datetime import datetime, timedelta
            import random
            
            for i in range(sample_claims):
                user = random.choice(users)
                claim_date = datetime.now() - timedelta(days=random.randint(1, 365))
                
                claim = Claim(
                    user_id=user.id,
                    policy_number=f'POL{random.randint(10000, 99999)}',
                    policy_type=random.choice(policy_types),
                    claim_type=random.choice(claim_types),
                    amount=random.uniform(1000, 100000),
                    incident_date=claim_date - timedelta(days=random.randint(1, 30)),
                    submission_date=claim_date,
                    incident_location=random.choice(locations),
                    description=f'Sample claim description #{i+1}',
                    status=random.choice(['submitted', 'under_review', 'processed']),
                    fraud_score=random.uniform(0, 100) if random.random() > 0.3 else None
                )
                
                if claim.status == 'processed':
                    claim.decision = random.choice(['approved', 'rejected'])
                    claim.decision_reason = f'Sample decision reason for claim #{i+1}'
                    claim.decision_date = claim_date + timedelta(days=random.randint(1, 14))
                
                db.session.add(claim)
            
            db.session.commit()
            print(f"Generated {sample_claims} sample claims")
            
            print("Sample data generation completed!")
        
        print("Database initialization completed successfully!")

@app.cli.command("train-models")
@click.option('--sample-size', default=1000, help='Number of training samples')
def train_models(sample_size):
    """Train AI models with sample data"""
    with app.app_context():
        try:
            print(f"Generating {sample_size} training samples...")
            training_data = generate_synthetic_training_data(sample_size)
            
            print("Training predictive model...")
            from app.ai_models import predictive_model
            features = []
            labels = []
            
            for claim in training_data:
                features.append({
                    'claim_amount': claim['claim_amount'],
                    'age_of_policy': claim['age_of_policy'],
                    'time_since_last_claim': claim.get('time_since_last_claim', 365),
                    'number_of_previous_claims': claim.get('number_of_previous_claims', 0),
                    'claim_type': claim['claim_type'],
                    'incident_location': claim.get('incident_location', 'unknown'),
                    'policy_type': claim.get('policy_type', 'unknown'),
                    'document_verification_score': claim['document_verification_score'],
                    'behavioral_anomaly_score': claim['behavioral_anomaly_score'],
                    'hidden_link_score': claim['hidden_link_score']
                })
                labels.append(claim['is_fraud'])
            
            results = predictive_model.train(features, labels)
            print(f"Model training completed! Validation accuracy: {results['val_metrics']['accuracy']:.2%}")
            
            print("Training behavioral model...")
            from app.ai_models import behavioral_ai
            behavioral_results = behavioral_ai.train_models(training_data)
            print(f"Behavioral model training completed! Samples: {behavioral_results['message']}")
            
            print("All models trained successfully!")
            
        except Exception as e:
            print(f"Error training models: {str(e)}")
            raise

@app.cli.command("create-user")
@click.argument('username')
@click.argument('email')
@click.argument('password')
@click.option('--role', default='user', help='User role (user, officer, admin)')
@click.option('--first-name', default='', help='First name')
@click.option('--last-name', default='', help='Last name')
def create_user(username, email, password, role, first_name, last_name):
    """Create a new user"""
    with app.app_context():
        user = User.query.filter_by(username=username).first()
        if user:
            print(f"User {username} already exists!")
            return
        
        user = User(
            username=username,
            email=email,
            first_name=first_name or username,
            last_name=last_name or 'User',
            role=role,
            is_active=True
        )
        user.set_password(password)
        
        db.session.add(user)
        db.session.commit()
        
        print(f"User {username} created successfully!")
        print(f"Username: {username}")
        print(f"Email: {email}")
        print(f"Role: {role}")
        print(f"Password: {password}")

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
