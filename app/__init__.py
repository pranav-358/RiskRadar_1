# CRITICAL: Set matplotlib backend BEFORE any other imports
import os
os.environ['MPLBACKEND'] = 'Agg'
import matplotlib
matplotlib.use('Agg', force=True)  # Force non-interactive backend

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_migrate import Migrate

# Initialize extensions
db = SQLAlchemy()
login_manager = LoginManager()
migrate = Migrate()

def create_app():
    app = Flask(__name__)
    
    # Configuration
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key')
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get(
        'DATABASE_URL', 
        'sqlite:///riskradar.db'
    )
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(__file__), 'static/uploads')
    app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
    
    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)
    migrate.init_app(app, db)
    
    # Configure login manager
    login_manager.login_view = 'main.login'
    login_manager.login_message_category = 'info'
    
    # Add user loader inside create_app to avoid circular imports
    from app.models import User
    
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))
    
    # Register blueprints - MOVE ALL IMPORTS INSIDE THE FUNCTION
    # This prevents circular imports
    with app.app_context():
        from app.main import main_bp
        from app.user import user_bp
        from app.admin import admin_bp
        from app.api import api_bp
        
        app.register_blueprint(main_bp)
        app.register_blueprint(user_bp, url_prefix='/user')
        app.register_blueprint(admin_bp, url_prefix='/admin')
        app.register_blueprint(api_bp, url_prefix='/api')
    
    # Create upload directory
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    
    # Add custom Jinja filters
    import json
    @app.template_filter('from_json')
    def from_json_filter(value):
        """Parse JSON string to Python object"""
        try:
            if isinstance(value, str):
                return json.loads(value)
            return value
        except:
            return {}
    
    # Initialize AI models (skip in testing mode)
    if not os.environ.get('SKIP_AI_INIT'):
        with app.app_context():
            from app.ai_models import predictive_model, behavioral_ai, hidden_link_ai
            predictive_model.load_model()
            behavioral_ai.load_models()
            hidden_link_ai.load_graph()
    
    return app
