#!/bin/bash

# ELHOSENY Laundry POS - Authentication Testing Script
# This script tests the web authentication flow using curl

set -e  # Exit on any error

# Configuration
BASE_URL="http://127.0.0.1:5000"
COOKIE_JAR="cookies.txt"
ADMIN_USERNAME="admin"
ADMIN_PASSWORD="${ADMIN_PASSWORD:-admin123!@#}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check if server is running
check_server() {
    print_status "Checking if server is running..."
    if curl -s --max-time 5 "${BASE_URL}/pos/login" > /dev/null; then
        print_success "Server is running at ${BASE_URL}"
    else
        print_error "Server is not running at ${BASE_URL}"
        echo "Please start the server with: python main.py"
        exit 1
    fi
}

# Function to test login page access
test_login_page() {
    print_status "Testing login page access..."
    
    response=$(curl -s -w "HTTPSTATUS:%{http_code}" "${BASE_URL}/pos/login")
    http_status=$(echo "$response" | tr -d '\n' | sed -e 's/.*HTTPSTATUS://')
    body=$(echo "$response" | sed -E 's/HTTPSTATUS:[0-9]{3}$//')
    
    if [[ "$http_status" == "200" ]]; then
        print_success "Login page accessible (HTTP 200)"
        
        # Check if page contains expected elements
        if echo "$body" | grep -q "ELHOSENY"; then
            print_success "Login page contains ELHOSENY branding"
        else
            print_warning "Login page might be missing branding"
        fi
        
        if echo "$body" | grep -qi "login\|sign"; then
            print_success "Login page contains login form"
        else
            print_warning "Login page might be missing login form"
        fi
    else
        print_error "Login page not accessible (HTTP $http_status)"
        echo "$body"
        exit 1
    fi
}

# Function to test successful login
test_successful_login() {
    print_status "Testing successful login..."
    
    # Clean up any existing cookies
    rm -f "$COOKIE_JAR"
    
    # Attempt login
    response=$(curl -s -w "HTTPSTATUS:%{http_code}REDIRECT:%{redirect_url}" \
        -c "$COOKIE_JAR" \
        -X POST \
        -d "username=${ADMIN_USERNAME}&password=${ADMIN_PASSWORD}" \
        "${BASE_URL}/pos/login")
    
    http_status=$(echo "$response" | tr -d '\n' | sed -e 's/.*HTTPSTATUS://' -e 's/REDIRECT:.*//')
    redirect_url=$(echo "$response" | tr -d '\n' | sed -e 's/.*REDIRECT://')
    
    if [[ "$http_status" == "302" ]]; then
        print_success "Login successful (HTTP 302 redirect)"
        
        # Check if cookies were set
        if [[ -f "$COOKIE_JAR" ]] && grep -q "session" "$COOKIE_JAR"; then
            print_success "Session cookie set successfully"
        else
            print_error "No session cookie found"
            return 1
        fi
        
        # Check redirect location
        if echo "$redirect_url" | grep -q "dashboard"; then
            print_success "Redirected to dashboard"
        else
            print_warning "Unexpected redirect location: $redirect_url"
        fi
    else
        print_error "Login failed (HTTP $http_status)"
        echo "$response"
        return 1
    fi
}

# Function to test failed login
test_failed_login() {
    print_status "Testing failed login with wrong password..."
    
    # Clean up any existing cookies
    rm -f "$COOKIE_JAR"
    
    # Attempt login with wrong password
    response=$(curl -s -w "HTTPSTATUS:%{http_code}" \
        -c "$COOKIE_JAR" \
        -X POST \
        -d "username=${ADMIN_USERNAME}&password=wrong-password" \
        "${BASE_URL}/pos/login")
    
    http_status=$(echo "$response" | tr -d '\n' | sed -e 's/.*HTTPSTATUS://')
    body=$(echo "$response" | sed -E 's/HTTPSTATUS:[0-9]{3}$//')
    
    if [[ "$http_status" == "200" ]]; then
        print_success "Failed login handled correctly (stayed on login page)"
        
        # Check for error message
        if echo "$body" | grep -qi "invalid\|incorrect\|error\|wrong"; then
            print_success "Error message displayed"
        else
            print_warning "No error message found (might be in flash messages)"
        fi
    else
        print_error "Unexpected response for failed login (HTTP $http_status)"
        return 1
    fi
}

# Function to test dashboard access with session
test_dashboard_access() {
    print_status "Testing dashboard access with session cookie..."
    
    # First ensure we're logged in
    test_successful_login
    
    # Try to access dashboard
    response=$(curl -s -w "HTTPSTATUS:%{http_code}" \
        -b "$COOKIE_JAR" \
        "${BASE_URL}/pos/dashboard")
    
    http_status=$(echo "$response" | tr -d '\n' | sed -e 's/.*HTTPSTATUS://')
    body=$(echo "$response" | sed -E 's/HTTPSTATUS:[0-9]{3}$//')
    
    if [[ "$http_status" == "200" ]]; then
        print_success "Dashboard accessible with session cookie"
        
        # Check if dashboard contains expected elements
        if echo "$body" | grep -qi "dashboard"; then
            print_success "Dashboard page loaded correctly"
        else
            print_warning "Dashboard page might not be fully loaded"
        fi
        
        if echo "$body" | grep -q "$ADMIN_USERNAME"; then
            print_success "User information displayed on dashboard"
        else
            print_warning "User information not found on dashboard"
        fi
    else
        print_error "Dashboard not accessible (HTTP $http_status)"
        echo "$body"
        return 1
    fi
}

# Function to test dashboard redirect without session
test_dashboard_redirect() {
    print_status "Testing dashboard redirect without session..."
    
    # Clean up cookies
    rm -f "$COOKIE_JAR"
    
    # Try to access dashboard without login
    response=$(curl -s -w "HTTPSTATUS:%{http_code}REDIRECT:%{redirect_url}" \
        --max-redirs 0 \
        "${BASE_URL}/pos/dashboard")
    
    http_status=$(echo "$response" | tr -d '\n' | sed -e 's/.*HTTPSTATUS://' -e 's/REDIRECT:.*//')
    redirect_url=$(echo "$response" | tr -d '\n' | sed -e 's/.*REDIRECT://')
    
    if [[ "$http_status" == "302" ]]; then
        print_success "Dashboard correctly redirects unauthorized access"
        
        if echo "$redirect_url" | grep -q "login"; then
            print_success "Redirected to login page"
        else
            print_warning "Unexpected redirect location: $redirect_url"
        fi
    else
        print_error "Dashboard should redirect unauthorized access (got HTTP $http_status)"
        return 1
    fi
}

# Function to test logout
test_logout() {
    print_status "Testing logout functionality..."
    
    # First ensure we're logged in
    test_successful_login
    
    # Verify we can access dashboard
    dashboard_response=$(curl -s -w "HTTPSTATUS:%{http_code}" \
        -b "$COOKIE_JAR" \
        "${BASE_URL}/pos/dashboard")
    
    dashboard_status=$(echo "$dashboard_response" | tr -d '\n' | sed -e 's/.*HTTPSTATUS://')
    
    if [[ "$dashboard_status" != "200" ]]; then
        print_error "Could not access dashboard before logout test"
        return 1
    fi
    
    # Logout
    logout_response=$(curl -s -w "HTTPSTATUS:%{http_code}REDIRECT:%{redirect_url}" \
        -b "$COOKIE_JAR" \
        -c "$COOKIE_JAR" \
        "${BASE_URL}/pos/logout")
    
    logout_status=$(echo "$logout_response" | tr -d '\n' | sed -e 's/.*HTTPSTATUS://' -e 's/REDIRECT:.*//')
    redirect_url=$(echo "$logout_response" | tr -d '\n' | sed -e 's/.*REDIRECT://')
    
    if [[ "$logout_status" == "302" ]]; then
        print_success "Logout successful (HTTP 302)"
        
        if echo "$redirect_url" | grep -q "login"; then
            print_success "Redirected to login page after logout"
        else
            print_warning "Unexpected redirect after logout: $redirect_url"
        fi
        
        # Test that we can't access dashboard anymore
        post_logout_response=$(curl -s -w "HTTPSTATUS:%{http_code}" \
            --max-redirs 0 \
            -b "$COOKIE_JAR" \
            "${BASE_URL}/pos/dashboard")
        
        post_logout_status=$(echo "$post_logout_response" | tr -d '\n' | sed -e 's/.*HTTPSTATUS://')
        
        if [[ "$post_logout_status" == "302" ]]; then
            print_success "Dashboard correctly requires re-authentication after logout"
        else
            print_error "Dashboard still accessible after logout (HTTP $post_logout_status)"
            return 1
        fi
    else
        print_error "Logout failed (HTTP $logout_status)"
        return 1
    fi
}

# Function to test session persistence
test_session_persistence() {
    print_status "Testing session persistence across requests..."
    
    # Login
    test_successful_login
    
    # Make multiple requests to verify session persistence
    for i in {1..3}; do
        response=$(curl -s -w "HTTPSTATUS:%{http_code}" \
            -b "$COOKIE_JAR" \
            "${BASE_URL}/pos/dashboard")
        
        http_status=$(echo "$response" | tr -d '\n' | sed -e 's/.*HTTPSTATUS://')
        
        if [[ "$http_status" == "200" ]]; then
            print_success "Request $i: Session persisted"
        else
            print_error "Request $i: Session lost (HTTP $http_status)"
            return 1
        fi
    done
}

# Function to test debug endpoint (if available)
test_debug_session() {
    print_status "Testing debug session endpoint..."
    
    # Login first
    test_successful_login
    
    # Try to access debug endpoint
    response=$(curl -s -w "HTTPSTATUS:%{http_code}" \
        -b "$COOKIE_JAR" \
        "${BASE_URL}/pos/debug/session")
    
    http_status=$(echo "$response" | tr -d '\n' | sed -e 's/.*HTTPSTATUS://')
    body=$(echo "$response" | sed -E 's/HTTPSTATUS:[0-9]{3}$//')
    
    if [[ "$http_status" == "200" ]]; then
        print_success "Debug session endpoint accessible"
        
        # Check if response contains session info
        if echo "$body" | grep -q "session\|cookies"; then
            print_success "Session debug info returned"
            
            # Pretty print JSON if jq is available
            if command -v jq &> /dev/null; then
                echo "$body" | jq . 2>/dev/null || echo "$body"
            else
                echo "$body"
            fi
        else
            print_warning "Debug endpoint response unexpected"
            echo "$body"
        fi
    elif [[ "$http_status" == "403" ]]; then
        print_warning "Debug endpoint disabled (production mode)"
    else
        print_warning "Debug endpoint not available (HTTP $http_status)"
    fi
}

# Function to run all tests
run_all_tests() {
    echo "==============================================="
    echo "ELHOSENY Laundry POS - Authentication Tests"
    echo "==============================================="
    echo
    
    local tests_passed=0
    local tests_failed=0
    
    # Array of test functions
    tests=(
        "check_server"
        "test_login_page"
        "test_failed_login"
        "test_successful_login"
        "test_dashboard_access"
        "test_dashboard_redirect"
        "test_logout"
        "test_session_persistence"
        "test_debug_session"
    )
    
    for test in "${tests[@]}"; do
        echo
        echo "Running: $test"
        echo "----------------------------------------"
        
        if $test; then
            ((tests_passed++))
        else
            ((tests_failed++))
            print_error "Test failed: $test"
        fi
    done
    
    echo
    echo "==============================================="
    echo "Test Results:"
    echo "  Passed: $tests_passed"
    echo "  Failed: $tests_failed"
    echo "==============================================="
    
    # Cleanup
    rm -f "$COOKIE_JAR"
    
    if [[ $tests_failed -eq 0 ]]; then
        print_success "All authentication tests passed!"
        exit 0
    else
        print_error "Some tests failed!"
        exit 1
    fi
}

# Show usage information
show_usage() {
    echo "Usage: $0 [command]"
    echo
    echo "Commands:"
    echo "  all              Run all authentication tests (default)"
    echo "  server           Check if server is running"
    echo "  login            Test login page access"
    echo "  auth             Test authentication flow"
    echo "  dashboard        Test dashboard access"
    echo "  logout           Test logout functionality"
    echo "  session          Test session persistence"
    echo "  debug            Test debug session endpoint"
    echo "  help             Show this help message"
    echo
    echo "Environment Variables:"
    echo "  ADMIN_PASSWORD   Admin password (default: admin123!@#)"
    echo
    echo "Examples:"
    echo "  $0                    # Run all tests"
    echo "  $0 auth               # Test authentication only"
    echo "  ADMIN_PASSWORD=mypass $0 login  # Test with custom password"
}

# Main script logic
case "${1:-all}" in
    "all")
        run_all_tests
        ;;
    "server")
        check_server
        ;;
    "login")
        check_server
        test_login_page
        ;;
    "auth")
        check_server
        test_login_page
        test_failed_login
        test_successful_login
        ;;
    "dashboard")
        check_server
        test_dashboard_access
        test_dashboard_redirect
        ;;
    "logout")
        check_server
        test_logout
        ;;
    "session")
        check_server
        test_session_persistence
        ;;
    "debug")
        check_server
        test_debug_session
        ;;
    "help"|"--help"|"-h")
        show_usage
        ;;
    *)
        print_error "Unknown command: $1"
        echo
        show_usage
        exit 1
        ;;
esac
