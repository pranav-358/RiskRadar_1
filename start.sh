#!/bin/bash

echo "===== RiskRadar Startup ====="

# Initialize database and create default users
echo "Initializing database..."
python << EOF
import os
os.environ['MPLBACKEND'] = 'Agg'

from app import create_app, db
from app.models import User, SystemConfig

app = create_app()

with app.app_context():
    # Create all tables
    db.create_all()
    print("✓ Database tables created")
    
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
        print("✓ Created admin user: admin@riskradar.com / admin123")
    
    # Create default regular user
    user = User.query.filter_by(username='user').first()
    if not user:
        user = User(
            username='user',
            email='user@example.com',
            first_name='Demo',
            last_name='User',
            role='user',
            is_active=True
        )
        user.set_password('user123')
        db.session.add(user)
        print("✓ Created demo user: user@example.com / user123")
    
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
    print("✓ Database initialization complete!")

EOF

# Train models if not already trained
if [ ! -f "training_data/models/gradient_boosting.joblib" ]; then
    echo "Training ML models..."
    python train_models.py || echo "⚠ Model training failed, will use fallback"
fi

# Start the Flask application
echo "Starting Flask application..."
python run.py
