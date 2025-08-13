import os
import logging
from datetime import timedelta
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from sqlalchemy.orm import DeclarativeBase
from werkzeug.middleware.proxy_fix import ProxyFix

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)
migrate = Migrate()
login_manager = LoginManager()
csrf = CSRFProtect()
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"]
)

def create_app(config_name='development'):
    app = Flask(__name__)
    
    # Load configuration
    from app.config import config
    app.config.from_object(config[config_name])
    
    # Set secret key from environment
    app.secret_key = os.environ.get("SESSION_SECRET", "dev-secret-key-change-in-production")
    
    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    csrf.init_app(app)
    limiter.init_app(app)
    
    # Configure CORS for API endpoints
    CORS(app, 
         supports_credentials=True,
         origins=['http://localhost:3000', 'http://127.0.0.1:3000'],
         expose_headers=['Content-Disposition'])
    
    # Configure Flask-Login
    login_manager.login_view = 'pos.login'
    login_manager.login_message = 'Please log in to access this page.'
    login_manager.login_message_category = 'info'
    login_manager.session_protection = 'strong'
    
    # Configure session
    app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=24)
    app.config['SESSION_COOKIE_NAME'] = 'session'
    app.config['SESSION_COOKIE_HTTPONLY'] = True
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
    app.config['SESSION_COOKIE_SECURE'] = False  # Set to True in production with HTTPS
    
    # Proxy fix for deployment
    app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)
    
    @login_manager.user_loader
    def load_user(user_id):
        from app.models import User
        return User.query.get(int(user_id))
    
    # Register blueprints
    from app.pos_routes import pos_bp
    from app.api_routes import api_v1_bp
    
    app.register_blueprint(pos_bp, url_prefix='/pos')
    app.register_blueprint(api_v1_bp, url_prefix='/api/v1')
    
    # Root redirect
    @app.route('/')
    def index():
        from flask import redirect, url_for
        return redirect(url_for('pos.login'))
    
    # Create tables and initial data
    with app.app_context():
        # Import models to ensure they're registered
        from app import models
        db.create_all()
        
        # Create initial admin user if not exists
        from app.models import User, Settings
        from werkzeug.security import generate_password_hash
        
        admin = User.query.filter_by(username='admin').first()
        if not admin:
            admin_password = os.environ.get('ADMIN_PASSWORD', 'admin123')
            admin = User(
                username='admin',
                password_hash=generate_password_hash(admin_password),
                role='admin'
            )
            db.session.add(admin)
            logger.info(f"Created admin user with password: {admin_password}")
        
        # Create default settings
        settings = Settings.query.first()
        if not settings:
            settings = Settings(
                app_name_en='ELHOSENY Laundry',
                app_name_ar='إلحسيني للمغاسل',
                primary_color='#2E5BBA',
                secondary_color='#00A8E6',
                accent_color='#E53E3E',
                currency='EGP',
                tax_rate=14.0,
                default_language='en'
            )
            db.session.add(settings)
        
        db.session.commit()
        
        # Create directories
        for directory in ['exports', 'backups', 'logs']:
            os.makedirs(directory, exist_ok=True)
    
    return app
