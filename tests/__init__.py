"""
ELHOSENY Laundry POS - Test Suite

This package contains comprehensive tests for the ELHOSENY Laundry POS system.

Test Categories:
- Authentication Flow Tests (test_auth_flow.py)
- API Flow Tests (test_api_flow.py)  
- Export Functionality Tests (test_export.py)

To run all tests:
    pytest tests/

To run specific test file:
    pytest tests/test_auth_flow.py -v

To run with coverage:
    pytest tests/ --cov=app --cov-report=html

Test Database:
    Tests use temporary SQLite databases that are created and destroyed
    for each test class to ensure isolation.

Environment Variables for Testing:
    - TESTING=True (automatically set)
    - WTF_CSRF_ENABLED=False (for easier testing)
    - SECRET_KEY=test-secret-key
    - JWT_SECRET_KEY=test-jwt-secret

Manual Testing:
    See scripts/test_auth.sh and scripts/test_api.sh for manual cURL tests
"""

import os
import sys

# Add the parent directory to the path so we can import the app
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Test configuration
TEST_CONFIG = {
    'TESTING': True,
    'WTF_CSRF_ENABLED': False,
    'SECRET_KEY': 'test-secret-key-change-in-production',
    'JWT_SECRET_KEY': 'test-jwt-secret-key',
    'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
    'ADMIN_PASSWORD': 'test-admin-password',
}

# Common test data
TEST_USERS = {
    'admin': {
        'username': 'admin',
        'password': 'test-admin-password',
        'role': 'admin',
        'permissions': '["all"]'
    },
    'cashier': {
        'username': 'cashier',
        'password': 'test-cashier-password',
        'role': 'cashier',
        'permissions': '["view_dashboard", "create_orders", "view_products", "view_customers"]'
    },
    'mobile_user': {
        'username': 'mobile_user',
        'password': 'test-mobile-password',
        'role': 'mobile_user',
        'permissions': '["mobile_access", "create_orders", "view_products"]'
    }
}

TEST_CATEGORIES = [
    {
        'name_en': 'Dry Cleaning',
        'name_ar': 'التنظيف الجاف',
        'description_en': 'Professional dry cleaning services',
        'description_ar': 'خدمات التنظيف الجاف المهنية'
    },
    {
        'name_en': 'Washing',
        'name_ar': 'الغسيل',
        'description_en': 'Regular washing services',
        'description_ar': 'خدمات الغسيل العادية'
    },
    {
        'name_en': 'Ironing',
        'name_ar': 'الكي',
        'description_en': 'Professional ironing services',
        'description_ar': 'خدمات الكي المهنية'
    }
]

TEST_PRODUCTS = [
    {
        'name_en': 'Shirt Wash',
        'name_ar': 'غسيل قميص',
        'price': 15.00,
        'cost_price': 8.00,
        'is_service': True
    },
    {
        'name_en': 'Suit Dry Clean',
        'name_ar': 'تنظيف بدلة جاف',
        'price': 45.00,
        'cost_price': 25.00,
        'is_service': True
    },
    {
        'name_en': 'Dress Ironing',
        'name_ar': 'كي فستان',
        'price': 20.00,
        'cost_price': 10.00,
        'is_service': True
    }
]

TEST_CUSTOMERS = [
    {
        'name_en': 'Ahmed Ali',
        'name_ar': 'أحمد علي',
        'phone': '01234567890',
        'email': 'ahmed.ali@example.com',
        'address_en': '123 Main Street, Cairo',
        'address_ar': '123 شارع الرئيسي، القاهرة'
    },
    {
        'name_en': 'Sarah Hassan',
        'name_ar': 'سارة حسن',
        'phone': '01987654321',
        'email': 'sarah.hassan@example.com',
        'address_en': '456 Nile Street, Alexandria',
        'address_ar': '456 شارع النيل، الإسكندرية'
    }
]

def create_test_data(app, db):
    """
    Create test data for testing purposes
    
    Args:
        app: Flask application instance
        db: SQLAlchemy database instance
    """
    from app.models import User, Category, Product, Customer
    from werkzeug.security import generate_password_hash
    
    with app.app_context():
        # Create test users
        for user_data in TEST_USERS.values():
            user = User(
                username=user_data['username'],
                password_hash=generate_password_hash(user_data['password']),
                role=user_data['role'],
                permissions=user_data['permissions']
            )
            db.session.add(user)
        
        # Create test categories
        categories = []
        for cat_data in TEST_CATEGORIES:
            category = Category(**cat_data, is_active=True)
            db.session.add(category)
            categories.append(category)
        
        db.session.flush()  # Flush to get IDs
        
        # Create test products
        for i, prod_data in enumerate(TEST_PRODUCTS):
            product = Product(
                **prod_data,
                category_id=categories[i % len(categories)].id,
                is_active=True
            )
            db.session.add(product)
        
        # Create test customers
        for cust_data in TEST_CUSTOMERS:
            customer = Customer(**cust_data, is_active=True)
            db.session.add(customer)
        
        db.session.commit()

def cleanup_test_data(db):
    """
    Clean up test data after tests
    
    Args:
        db: SQLAlchemy database instance
    """
    # This will be called by test teardown methods
    # For SQLite in-memory databases, this is usually not needed
    # as the database is destroyed when the connection closes
    pass

# Test utilities
class TestHelpers:
    """Helper functions for testing"""
    
    @staticmethod
    def login_user(client, username, password):
        """
        Helper to login a user via the web interface
        
        Args:
            client: Flask test client
            username: Username to login with
            password: Password to login with
            
        Returns:
            Response object from login attempt
        """
        return client.post('/pos/login', data={
            'username': username,
            'password': password
        }, follow_redirects=True)
    
    @staticmethod
    def get_api_token(client, username, password):
        """
        Helper to get JWT token for API testing
        
        Args:
            client: Flask test client
            username: Username to authenticate with
            password: Password to authenticate with
            
        Returns:
            JWT token string or None if failed
        """
        response = client.post('/api/v1/auth/token', json={
            'username': username,
            'password': password
        })
        
        if response.status_code == 200:
            return response.get_json()['token']
        return None
    
    @staticmethod
    def make_authenticated_request(client, method, url, token, **kwargs):
        """
        Helper to make authenticated API requests
        
        Args:
            client: Flask test client
            method: HTTP method ('get', 'post', etc.)
            url: URL to request
            token: JWT token for authentication
            **kwargs: Additional arguments for the request
            
        Returns:
            Response object
        """
        headers = kwargs.get('headers', {})
        headers['Authorization'] = f'Bearer {token}'
        kwargs['headers'] = headers
        
        method_func = getattr(client, method.lower())
        return method_func(url, **kwargs)
    
    @staticmethod
    def assert_api_error(response, expected_status=400, error_field='error'):
        """
        Helper to assert API error responses
        
        Args:
            response: Response object to check
            expected_status: Expected HTTP status code
            error_field: Field name that should contain error message
        """
        assert response.status_code == expected_status
        data = response.get_json()
        assert error_field in data
        assert data[error_field]  # Error message should not be empty
    
    @staticmethod
    def assert_api_success(response, expected_status=200, required_fields=None):
        """
        Helper to assert successful API responses
        
        Args:
            response: Response object to check
            expected_status: Expected HTTP status code
            required_fields: List of fields that must be present in response
        """
        assert response.status_code == expected_status
        data = response.get_json()
        
        if required_fields:
            for field in required_fields:
                assert field in data, f"Required field '{field}' missing from response"

# Export test helpers for use in test files
__all__ = [
    'TEST_CONFIG',
    'TEST_USERS', 
    'TEST_CATEGORIES',
    'TEST_PRODUCTS',
    'TEST_CUSTOMERS',
    'create_test_data',
    'cleanup_test_data',
    'TestHelpers'
]
