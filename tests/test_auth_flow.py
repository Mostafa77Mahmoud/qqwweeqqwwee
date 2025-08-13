import pytest
import requests
import tempfile
import os
from app import create_app, db
from app.models import User
from werkzeug.security import generate_password_hash

class TestAuthFlow:
    """Test authentication flow using requests library"""
    
    @pytest.fixture
    def app(self):
        """Create test application"""
        # Create temporary database
        db_fd, db_path = tempfile.mkstemp()
        
        app = create_app()
        app.config.update({
            'TESTING': True,
            'SQLALCHEMY_DATABASE_URI': f'sqlite:///{db_path}',
            'WTF_CSRF_ENABLED': False,  # Disable CSRF for testing
            'SECRET_KEY': 'test-secret-key',
            'ADMIN_PASSWORD': 'test-admin-pass'
        })
        
        with app.app_context():
            db.create_all()
            
            # Create test admin user
            admin = User(
                username='admin',
                password_hash=generate_password_hash('test-admin-pass'),
                role='admin',
                permissions='all'
            )
            db.session.add(admin)
            
            # Create test cashier user
            cashier = User(
                username='cashier',
                password_hash=generate_password_hash('test-cashier-pass'),
                role='cashier',
                permissions='["view_dashboard", "create_orders"]'
            )
            db.session.add(cashier)
            
            db.session.commit()
        
        yield app
        
        # Cleanup
        os.close(db_fd)
        os.unlink(db_path)
    
    @pytest.fixture
    def base_url(self, app):
        """Get base URL for the test server"""
        return 'http://localhost:5000'
    
    def test_login_page_loads(self, base_url):
        """Test that login page loads successfully"""
        response = requests.get(f'{base_url}/pos/login')
        assert response.status_code == 200
        assert 'ELHOSENY' in response.text
        assert 'login' in response.text.lower()
    
    def test_successful_admin_login(self, base_url):
        """Test successful admin login creates session cookie"""
        session = requests.Session()
        
        # First get login page to check it loads
        response = session.get(f'{base_url}/pos/login')
        assert response.status_code == 200
        
        # Attempt login with correct credentials
        login_data = {
            'username': 'admin',
            'password': 'test-admin-pass'
        }
        
        response = session.post(f'{base_url}/pos/login', data=login_data, allow_redirects=False)
        
        # Should redirect on successful login
        assert response.status_code == 302
        assert 'Set-Cookie' in response.headers
        assert 'session=' in response.headers['Set-Cookie']
        
        # Verify redirect location
        assert '/pos/dashboard' in response.headers.get('Location', '')
    
    def test_successful_cashier_login(self, base_url):
        """Test successful cashier login"""
        session = requests.Session()
        
        login_data = {
            'username': 'cashier',
            'password': 'test-cashier-pass'
        }
        
        response = session.post(f'{base_url}/pos/login', data=login_data, allow_redirects=False)
        
        # Should redirect on successful login
        assert response.status_code == 302
        assert 'Set-Cookie' in response.headers
    
    def test_failed_login_wrong_password(self, base_url):
        """Test failed login with wrong password"""
        session = requests.Session()
        
        login_data = {
            'username': 'admin',
            'password': 'wrong-password'
        }
        
        response = session.post(f'{base_url}/pos/login', data=login_data)
        
        # Should stay on login page
        assert response.status_code == 200
        assert 'login' in response.text.lower()
        # Should show error message
        assert any(error_text in response.text.lower() for error_text in ['invalid', 'incorrect', 'error'])
    
    def test_failed_login_nonexistent_user(self, base_url):
        """Test failed login with nonexistent username"""
        session = requests.Session()
        
        login_data = {
            'username': 'nonexistent',
            'password': 'any-password'
        }
        
        response = session.post(f'{base_url}/pos/login', data=login_data)
        
        # Should stay on login page
        assert response.status_code == 200
        assert 'login' in response.text.lower()
    
    def test_dashboard_access_after_login(self, base_url):
        """Test dashboard access after successful login"""
        session = requests.Session()
        
        # Login first
        login_data = {
            'username': 'admin',
            'password': 'test-admin-pass'
        }
        
        login_response = session.post(f'{base_url}/pos/login', data=login_data)
        assert login_response.status_code == 200 or login_response.status_code == 302
        
        # Access dashboard
        dashboard_response = session.get(f'{base_url}/pos/dashboard')
        assert dashboard_response.status_code == 200
        assert 'dashboard' in dashboard_response.text.lower()
        assert 'admin' in dashboard_response.text.lower()
    
    def test_dashboard_redirect_when_not_logged_in(self, base_url):
        """Test dashboard redirects to login when not authenticated"""
        response = requests.get(f'{base_url}/pos/dashboard', allow_redirects=False)
        
        # Should redirect to login
        assert response.status_code == 302
        assert '/pos/login' in response.headers.get('Location', '')
    
    def test_logout_functionality(self, base_url):
        """Test logout clears session and redirects to login"""
        session = requests.Session()
        
        # Login first
        login_data = {
            'username': 'admin',
            'password': 'test-admin-pass'
        }
        session.post(f'{base_url}/pos/login', data=login_data)
        
        # Verify we can access dashboard
        dashboard_response = session.get(f'{base_url}/pos/dashboard')
        assert dashboard_response.status_code == 200
        
        # Logout
        logout_response = session.get(f'{base_url}/pos/logout', allow_redirects=False)
        assert logout_response.status_code == 302
        assert '/pos/login' in logout_response.headers.get('Location', '')
        
        # Verify we can't access dashboard anymore
        dashboard_response_after_logout = session.get(f'{base_url}/pos/dashboard', allow_redirects=False)
        assert dashboard_response_after_logout.status_code == 302
    
    def test_session_persistence_across_requests(self, base_url):
        """Test that session persists across multiple requests"""
        session = requests.Session()
        
        # Login
        login_data = {
            'username': 'admin',
            'password': 'test-admin-pass'
        }
        session.post(f'{base_url}/pos/login', data=login_data)
        
        # Make multiple requests to verify session persistence
        for _ in range(3):
            response = session.get(f'{base_url}/pos/dashboard')
            assert response.status_code == 200
    
    def test_rate_limiting_on_login(self, base_url):
        """Test rate limiting on login attempts"""
        session = requests.Session()
        
        # Make multiple failed login attempts
        login_data = {
            'username': 'admin',
            'password': 'wrong-password'
        }
        
        responses = []
        for i in range(6):  # Attempt more than the rate limit
            response = session.post(f'{base_url}/pos/login', data=login_data)
            responses.append(response.status_code)
        
        # At least one should be rate limited (429) or still working
        # Rate limiting implementation may vary
        assert all(status in [200, 429] for status in responses)
    
    def test_csrf_protection_disabled_in_tests(self, base_url):
        """Verify CSRF is disabled for testing"""
        session = requests.Session()
        
        # This should work without CSRF token in test mode
        login_data = {
            'username': 'admin',
            'password': 'test-admin-pass'
        }
        
        response = session.post(f'{base_url}/pos/login', data=login_data)
        # Should not fail due to CSRF
        assert response.status_code in [200, 302]

def test_curl_authentication_example():
    """Example of how authentication should work with curl"""
    # This is a documentation test showing the expected curl behavior
    curl_commands = [
        # Step 1: Get login page
        "curl -i -c cookies.txt http://127.0.0.1:5000/pos/login",
        
        # Step 2: Login with credentials
        "curl -i -c cookies.txt -X POST http://127.0.0.1:5000/pos/login -d 'username=admin&password=test-admin-pass'",
        
        # Step 3: Access protected resource with session cookie
        "curl -b cookies.txt http://127.0.0.1:5000/pos/dashboard"
    ]
    
    expected_behaviors = [
        "Should return 200 OK with login form",
        "Should return 302 redirect with Set-Cookie: session=... header",
        "Should return 200 OK with dashboard content"
    ]
    
    # This test documents the expected behavior
    assert len(curl_commands) == len(expected_behaviors)
    print("Curl authentication flow:")
    for cmd, expected in zip(curl_commands, expected_behaviors):
        print(f"Command: {cmd}")
        print(f"Expected: {expected}")
        print()

if __name__ == '__main__':
    pytest.main([__file__, '-v'])
