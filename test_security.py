"""
Security and Functionality Test Script
Tests the fixes applied to resolve Internal Server Error and security vulnerabilities
"""

import requests
from requests.exceptions import RequestException

BASE_URL = "http://127.0.0.1:5000"

def print_test(test_name, passed, details=""):
    status = "✅ PASS" if passed else "❌ FAIL"
    print(f"\n{status}: {test_name}")
    if details:
        print(f"   Details: {details}")

def test_1_unauthenticated_admin_access():
    """Test 1: Accessing /admin/home without login should redirect to login"""
    print("\n" + "="*60)
    print("TEST 1: Unauthenticated Admin Access")
    print("="*60)
    
    try:
        response = requests.get(f"{BASE_URL}/admin/home", allow_redirects=False)
        
        # Should get a redirect (302)
        is_redirect = response.status_code in [302, 303, 307, 308]
        redirects_to_login = '/login' in response.headers.get('Location', '')
        
        passed = is_redirect and redirects_to_login
        print_test(
            "Unauthenticated access blocked",
            passed,
            f"Status: {response.status_code}, Redirects to: {response.headers.get('Location', 'N/A')}"
        )
        return passed
    except RequestException as e:
        print_test("Unauthenticated access blocked", False, f"Error: {e}")
        return False

def test_2_admin_login():
    """Test 2: Admin login should work and redirect to dashboard"""
    print("\n" + "="*60)
    print("TEST 2: Admin Login Flow")
    print("="*60)
    
    try:
        session = requests.Session()
        
        # First get the login page to establish session
        session.get(f"{BASE_URL}/login")
        
        # Attempt login
        login_data = {
            'loginId': 'admin@pgpc.edu',
            'password': 'adminpass',
            'role': 'staff'
        }
        
        response = session.post(f"{BASE_URL}/login", data=login_data, allow_redirects=False)
        
        # Should redirect after successful login
        is_redirect = response.status_code in [302, 303, 307, 308]
        redirects_to_admin = '/admin' in response.headers.get('Location', '')
        
        passed = is_redirect and redirects_to_admin
        print_test(
            "Admin login successful",
            passed,
            f"Status: {response.status_code}, Redirects to: {response.headers.get('Location', 'N/A')}"
        )
        
        # Test 2b: Access admin dashboard after login
        if passed:
            response = session.get(f"{BASE_URL}/admin/home")
            dashboard_works = response.status_code == 200 and 'Internal Server Error' not in response.text
            print_test(
                "Admin dashboard loads without error",
                dashboard_works,
                f"Status: {response.status_code}, Has error: {'Internal Server Error' in response.text}"
            )
            return dashboard_works
        
        return passed
    except RequestException as e:
        print_test("Admin login", False, f"Error: {e}")
        return False

def test_3_student_login():
    """Test 3: Student login should work"""
    print("\n" + "="*60)
    print("TEST 3: Student Login Flow")
    print("="*60)
    
    try:
        session = requests.Session()
        
        # Get login page
        session.get(f"{BASE_URL}/login")
        
        # Attempt student login
        login_data = {
            'loginId': 'P202400920',
            'password': 'studentpass',
            'role': 'student'
        }
        
        response = session.post(f"{BASE_URL}/login", data=login_data, allow_redirects=False)
        
        # Should redirect after successful login
        is_redirect = response.status_code in [302, 303, 307, 308]
        location = response.headers.get('Location', '')
        redirects_correctly = '/student' in location or '/change-password' in location
        
        passed = is_redirect and redirects_correctly
        print_test(
            "Student login successful",
            passed,
            f"Status: {response.status_code}, Redirects to: {location}"
        )
        return passed
    except RequestException as e:
        print_test("Student login", False, f"Error: {e}")
        return False

def test_4_role_based_access():
    """Test 4: Students should not access admin routes"""
    print("\n" + "="*60)
    print("TEST 4: Role-Based Access Control")
    print("="*60)
    
    try:
        session = requests.Session()
        
        # Login as student
        session.get(f"{BASE_URL}/login")
        login_data = {
            'loginId': 'P202400920',
            'password': 'studentpass',
            'role': 'student'
        }
        session.post(f"{BASE_URL}/login", data=login_data)
        
        # Try to access admin route
        response = session.get(f"{BASE_URL}/admin/home", allow_redirects=False)
        
        # Should be blocked (redirect to login or error)
        is_blocked = response.status_code in [302, 303, 307, 308, 403]
        
        print_test(
            "Student blocked from admin routes",
            is_blocked,
            f"Status: {response.status_code}"
        )
        return is_blocked
    except RequestException as e:
        print_test("Role-based access control", False, f"Error: {e}")
        return False

def test_5_cache_headers():
    """Test 5: Sensitive pages should have no-cache headers"""
    print("\n" + "="*60)
    print("TEST 5: Cache Control Headers")
    print("="*60)
    
    try:
        session = requests.Session()
        
        # Login as admin
        session.get(f"{BASE_URL}/login")
        login_data = {
            'loginId': 'admin@pgpc.edu',
            'password': 'adminpass',
            'role': 'staff'
        }
        session.post(f"{BASE_URL}/login", data=login_data)
        
        # Access admin dashboard
        response = session.get(f"{BASE_URL}/admin/home")
        
        # Check for no-cache headers
        cache_control = response.headers.get('Cache-Control', '')
        has_no_cache = 'no-cache' in cache_control or 'no-store' in cache_control
        
        print_test(
            "No-cache headers present",
            has_no_cache,
            f"Cache-Control: {cache_control}"
        )
        return has_no_cache
    except RequestException as e:
        print_test("Cache headers", False, f"Error: {e}")
        return False

def main():
    print("\n" + "="*60)
    print("PGPC SIS - SECURITY & FUNCTIONALITY TEST SUITE")
    print("="*60)
    print(f"Testing server at: {BASE_URL}")
    
    results = []
    
    # Run all tests
    results.append(("Unauthenticated Access Block", test_1_unauthenticated_admin_access()))
    results.append(("Admin Login & Dashboard", test_2_admin_login()))
    results.append(("Student Login", test_3_student_login()))
    results.append(("Role-Based Access Control", test_4_role_based_access()))
    results.append(("Cache Control Headers", test_5_cache_headers()))
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {test_name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed! The application is secure and functional.")
    else:
        print(f"\n⚠️  {total - passed} test(s) failed. Please review the issues above.")
    
    return passed == total

if __name__ == "__main__":
    try:
        success = main()
        exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\nTests interrupted by user.")
        exit(1)
    except Exception as e:
        print(f"\n\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
