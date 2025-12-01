import requests

print("Testing security fixes...")
print("-" * 50)

# Test 1: Unauthenticated access
print("\n1. Testing unauthenticated access to /admin/home")
try:
    r = requests.get('http://127.0.0.1:5000/admin/home', allow_redirects=False)
    print(f"   Status: {r.status_code}")
    print(f"   Location: {r.headers.get('Location', 'None')}")
    if r.status_code in [302, 303] and 'login' in r.headers.get('Location', ''):
        print("   ✅ PASS: Redirects to login")
    else:
        print("   ❌ FAIL: Should redirect to login")
except Exception as e:
    print(f"   ❌ ERROR: {e}")

# Test 2: Admin login
print("\n2. Testing admin login")
try:
    session = requests.Session()
    session.get('http://127.0.0.1:5000/login')
    
    r = session.post('http://127.0.0.1:5000/login', 
                     data={'loginId': 'admin@pgpc.edu', 'password': 'adminpass', 'role': 'staff'},
                     allow_redirects=False)
    print(f"   Status: {r.status_code}")
    print(f"   Location: {r.headers.get('Location', 'None')}")
    
    if r.status_code in [302, 303]:
        # Now try to access admin dashboard
        r2 = session.get('http://127.0.0.1:5000/admin/home')
        print(f"   Dashboard Status: {r2.status_code}")
        if r2.status_code == 200 and 'Internal Server Error' not in r2.text:
            print("   ✅ PASS: Admin dashboard loads successfully")
        else:
            print("   ❌ FAIL: Dashboard has errors")
    else:
        print("   ❌ FAIL: Login failed")
except Exception as e:
    print(f"   ❌ ERROR: {e}")

# Test 3: Student cannot access admin
print("\n3. Testing student access to admin routes")
try:
    session = requests.Session()
    session.get('http://127.0.0.1:5000/login')
    
    session.post('http://127.0.0.1:5000/login',
                 data={'loginId': 'P202400920', 'password': 'studentpass', 'role': 'student'})
    
    r = session.get('http://127.0.0.1:5000/admin/home', allow_redirects=False)
    print(f"   Status: {r.status_code}")
    
    if r.status_code in [302, 303, 403]:
        print("   ✅ PASS: Student blocked from admin routes")
    else:
        print("   ❌ FAIL: Student should be blocked")
except Exception as e:
    print(f"   ❌ ERROR: {e}")

print("\n" + "-" * 50)
print("Testing complete!")
