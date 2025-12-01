#!/usr/bin/env python3
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from webapp import create_app
from webapp.models import db, User
from werkzeug.security import generate_password_hash

app = create_app()

with app.app_context():
    # Create admin user if not exists
    admin = User.query.filter_by(email='admin@pgpc.edu').first()
    if not admin:
        admin = User(
            name='Admin User',
            email='admin@pgpc.edu',
            password_hash=generate_password_hash('adminpass', method='pbkdf2:sha256'),
            role='staff'
        )
        db.session.add(admin)
        db.session.commit()
        print("Admin user created")
    else:
        print("Admin user already exists")

print("Test completed. Try logging in with admin@pgpc.edu / adminpass")