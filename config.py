import os
from datetime import timedelta
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Config:
    """Base configuration"""
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', 'sqlite:///riskradar.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Upload configuration
    UPLOAD_FOLDER = os.environ.get('UPLOAD_FOLDER', os.path.join(os.path.dirname(__file__), 'app/static/uploads'))
    MAX_CONTENT_LENGTH = int(os.environ.get('MAX_CONTENT_LENGTH', 16 * 1024 * 1024))  # 16MB
    
    # Session configuration
    PERMANENT_SESSION_LIFETIME = timedelta(days=7)
    
    # AI Model paths
    MODEL_DIR = os.environ.get('MODEL_DIR', os.path.join(os.path.dirname(__file__), 'models'))
    
    # Risk thresholds
    RISK_THRESHOLD_HIGH = int(os.environ.get('FRAUD_THRESHOLD_HIGH', 75))
    RISK_THRESHOLD_MEDIUM = int(os.environ.get('FRAUD_THRESHOLD_MEDIUM', 50))
    RISK_THRESHOLD_LOW = int(os.environ.get('FRAUD_THRESHOLD_LOW', 30))
    
    # Application settings
    AUTO_ASSIGN_OFFICERS = os.environ.get('AUTO_ASSIGN_OFFICERS', 'True').lower() == 'true'
    BATCH_PROCESSING_LIMIT = int(os.environ.get('BATCH_PROCESSING_LIMIT', 100))
    
    # OCR Configuration
    USE_EASYOCR = os.environ.get('USE_EASYOCR', 'True').lower() == 'true'
    TESSERACT_PATH = os.environ.get('TESSERACT_PATH', '/usr/bin/tesseract')
    
    # Email Configuration
    MAIL_SERVER = os.environ.get('MAIL_SERVER', '')
    MAIL_PORT = int(os.environ.get('MAIL_PORT', 587))
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'True').lower() == 'true'
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME', '')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD', '')
    
    # Logging Configuration
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')
    LOG_FILE = os.environ.get('LOG_FILE', os.path.join(os.path.dirname(__file__), 'logs/riskradar.log'))

class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    SQLALCHEMY_ECHO = True

class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False
    SQLALCHEMY_ECHO = False
    
    # Use production database
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', '').replace(
        'postgres://', 'postgresql://'
    )

class TestingConfig(Config):
    """Testing configuration"""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False

# Configuration dictionary
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}
