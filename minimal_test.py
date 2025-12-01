#!/usr/bin/env python3
import os
import sys
import traceback

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

print("=== MINIMAL TEST START ===")

try:
    print("1. Testing imports...")
    from flask import Flask
    print("   ✓ Flask imported")
    
    from webapp.database import db
    print("   ✓ Database imported")
    
    from webapp.models import User, Student
    print("   ✓ Models imported")
    
    print("2. Testing app creation...")
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'test-key'
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///test.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    db.init_app(app)
    print("   ✓ Basic app created")
    
    print("3. Testing database...")
    with app.app_context():
        db.create_all()
        print("   ✓ Database tables created")
    
    print("4. Testing routes...")
    @app.route('/')
    def test_route():
        return "Test successful!"
    
    print("   ✓ Route created")
    
    print("5. Starting minimal server...")
    app.run(debug=True, port=5001, host='127.0.0.1')
    
except ImportError as e:
    print(f"❌ IMPORT ERROR: {e}")
    traceback.print_exc()
except Exception as e:
    print(f"❌ ERROR: {e}")
    traceback.print_exc()

print("=== MINIMAL TEST END ===")