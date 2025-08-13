import jwt
from datetime import datetime, timedelta
from functools import wraps
from flask import request, jsonify, current_app, session
from flask_login import current_user
from werkzeug.security import check_password_hash
from app.models import User

def generate_jwt_token(user):
    """Generate JWT token for mobile API authentication"""
    payload = {
        'user_id': user.id,
        'username': user.username,
        'role': user.role,
        'exp': datetime.utcnow() + current_app.config['JWT_ACCESS_TOKEN_EXPIRES'],
        'iat': datetime.utcnow(),
        'type': 'access'
    }
    
    token = jwt.encode(
        payload,
        current_app.config['JWT_SECRET_KEY'],
        algorithm='HS256'
    )
    
    return token

def generate_refresh_token(user):
    """Generate refresh token for mobile API"""
    payload = {
        'user_id': user.id,
        'exp': datetime.utcnow() + current_app.config['JWT_REFRESH_TOKEN_EXPIRES'],
        'iat': datetime.utcnow(),
        'type': 'refresh'
    }
    
    token = jwt.encode(
        payload,
        current_app.config['JWT_SECRET_KEY'],
        algorithm='HS256'
    )
    
    return token

def verify_jwt_token(token):
    """Verify and decode JWT token"""
    try:
        payload = jwt.decode(
            token,
            current_app.config['JWT_SECRET_KEY'],
            algorithms=['HS256']
        )
        
        if payload['type'] != 'access':
            return None
            
        user = User.query.get(payload['user_id'])
        if user and user.is_active:
            return user
            
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None
    
    return None

def jwt_required(f):
    """Decorator for JWT authentication on API endpoints"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = None
        
        # Get token from Authorization header
        auth_header = request.headers.get('Authorization')
        if auth_header and auth_header.startswith('Bearer '):
            token = auth_header.split(' ')[1]
        
        if not token:
            return jsonify({'error': 'Token is missing'}), 401
        
        user = verify_jwt_token(token)
        if not user:
            return jsonify({'error': 'Token is invalid or expired'}), 401
        
        # Add current user to request context
        request.current_user = user
        return f(*args, **kwargs)
    
    return decorated_function

def authenticate_user(username, password):
    """Authenticate user with username and password"""
    user = User.query.filter_by(username=username, is_active=True).first()
    
    if user and check_password_hash(user.password_hash, password):
        return user
    
    return None

def has_permission(permission):
    """Decorator to check user permissions"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                return jsonify({'error': 'Authentication required'}), 401
            
            if not current_user.has_permission(permission):
                return jsonify({'error': 'Insufficient permissions'}), 403
            
            return f(*args, **kwargs)
        
        return decorated_function
    return decorator

def log_security_event(event_type, details, user_id=None):
    """Log security-related events"""
    import logging
    
    logger = logging.getLogger(__name__)
    
    if user_id is None and current_user.is_authenticated:
        user_id = current_user.id
    
    log_data = {
        'event_type': event_type,
        'user_id': user_id,
        'details': details,
        'ip_address': request.remote_addr,
        'user_agent': request.headers.get('User-Agent'),
        'timestamp': datetime.utcnow().isoformat()
    }
    
    logger.warning(f"Security Event: {log_data}")

def get_user_language():
    """Get user's preferred language from session"""
    return session.get('language', 'en')

def set_user_language(language):
    """Set user's preferred language in session"""
    if language in ['en', 'ar']:
        session['language'] = language
        session.permanent = True
