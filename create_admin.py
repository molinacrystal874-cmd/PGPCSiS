#!/usr/bin/env python3
"""
Script to create a default admin user for the PGPCSiS system.
Run this script to create an admin account with email 'admin' and password 'adminpass'.
"""

import os
import sys

# Add the webapp directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'webapp'))

from webapp import create_app
from webapp.database import db
from webapp.models import User
from werkzeug.security import generate_password_hash

def create_admin_user():
    """Create the default admin user."""
    app = create_app()
    
    with app.app_context():
        try:
            # Check if admin already exists
            existing_admin = User.query.filter_by(email='admin@pgpc.edu').first()
            if existing_admin:
                print("Admin user already exists!")
                print(f"   Email: {existing_admin.email}")
                print(f"   Name: {existing_admin.name}")
                return True
            
            # Create admin user
            admin_user = User(
                email='admin@pgpc.edu',
                password_hash=generate_password_hash('adminpass', method='pbkdf2:sha256'),
                role='staff',
                name='System Administrator'
            )
            
            db.session.add(admin_user)
            db.session.commit()
            
            print("Admin user created successfully!")
            print("   Email: admin@pgpc.edu")
            print("   Password: adminpass")
            print("   Role: staff")
            
            return True
            
        except Exception as e:
            db.session.rollback()
            print(f"Error creating admin user: {e}")
            return False

if __name__ == '__main__':
    print("Creating default admin user...")
    success = create_admin_user()
    
    if success:
        print("\nAdmin user setup completed!")
        print("\nLogin Details:")
        print("Email: admin@pgpc.edu")
        print("Password: adminpass")
        print("Role: Staff")
        print("\nYou can now log in to the admin panel.")
    else:
        print("\nFailed to create admin user. Please check the error messages above.")
        sys.exit(1)