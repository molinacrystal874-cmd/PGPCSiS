#!/usr/bin/env python3
"""
Test login functionality
"""

from webapp import create_app
from webapp.database import db
from webapp.models import User, Student
from werkzeug.security import check_password_hash

def test_login():
    app = create_app()
    
    with app.app_context():
        print("=== TESTING LOGIN CREDENTIALS ===")
        
        # Test admin login
        admin = User.query.filter_by(email='admin@pgpc.edu').first()
        if admin:
            print(f"✓ Admin found: {admin.email}")
            if check_password_hash(admin.password_hash, 'admin123'):
                print("✓ Admin password correct")
            else:
                print("✗ Admin password incorrect")
        else:
            print("✗ Admin not found")
        
        # Test student login
        student = Student.query.filter_by(student_id='TEST001').first()
        if student:
            print(f"✓ Student found: {student.student_id}")
            if check_password_hash(student.password_hash, 'student123'):
                print("✓ Student password correct")
            else:
                print("✗ Student password incorrect")
        else:
            print("✗ Student not found")
        
        print("\n=== LOGIN INSTRUCTIONS ===")
        print("1. Start the app: python run.py")
        print("2. Go to: http://localhost:5000")
        print("3. Login as Admin:")
        print("   - Role: Staff")
        print("   - Email: admin@pgpc.edu")
        print("   - Password: admin123")
        print("4. Or login as Student:")
        print("   - Role: Student")
        print("   - Student ID: TEST001")
        print("   - Password: student123")

if __name__ == '__main__':
    test_login()