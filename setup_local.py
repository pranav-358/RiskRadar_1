#!/usr/bin/env python
"""
Local Setup Script for RiskRadar
Run this after cloning the repo and installing requirements
"""

import os
import sys

def setup_database():
    """Initialize database and create default users"""
    print("=" * 50)
    print("RiskRadar Local Setup")
    print("=" * 50)
    
    # Set matplotlib backend before importing app
    os.environ['MPLBACKEND'] = 'Agg'
    os.environ['SKIP_AI_INIT'] = '1'  # Skip AI initialization during setup
    
    try:
        from app import create_app, db
        from app.models import User, SystemConfig
        
        print("\n✓ Imports successful")
        
        app = create_app()
        
        with app.app_context():
            print("\n📦 Creating database tables...")
            db.create_all()
            print("✓ Database tables created")
            
            # Check if admin user already exists
            existing_admin = User.query.filter_by(username='admin').first()
            if existing_admin:
                print("\n⚠️  Admin user already exists")
            else:
                print("\n👤 Creating admin user...")
                admin = User(
                    username='admin',
                    email='admin@riskradar.com',
                    first_name='System',
                    last_name='Administrator',
                    role='admin',
                    is_active=True
                )
                admin.set_password('admin123')
                db.session.add(admin)
                print("✓ Admin user created: admin / admin123")
            
            # Check if demo user already exists
            existing_user = User.query.filter_by(username='user').first()
            if existing_user:
                print("⚠️  Demo user already exists")
            else:
                print("\n👤 Creating demo user...")
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
                print("✓ Demo user created: user / user123")
            
            # Create default system configuration
            print("\n⚙️  Creating system configuration...")
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
            print("✓ System configuration created")
            
            # Display summary
            total_users = User.query.count()
            print("\n" + "=" * 50)
            print("✅ Setup Complete!")
            print("=" * 50)
            print(f"📊 Total users in database: {total_users}")
            print("\n🔐 Login Credentials:")
            print("   Admin: admin / admin123")
            print("   User:  user / user123")
            print("\n🚀 Start the application with:")
            print("   python run.py")
            print("\n🌐 Then open: http://127.0.0.1:7860")
            print("=" * 50)
            
    except Exception as e:
        print(f"\n❌ Error during setup: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    setup_database()
