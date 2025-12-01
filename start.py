#!/usr/bin/env python3
"""
Startup script for PGPCSiS application
"""

import os
import sys

def main():
    print("Starting PGPCSiS Application...")
    
    # Check if .env file exists
    if not os.path.exists('.env'):
        print("WARNING: .env file not found. Creating from .env.example...")
        if os.path.exists('.env.example'):
            import shutil
            shutil.copy('.env.example', '.env')
            print("Please edit .env file with your database credentials")
        else:
            print("ERROR: .env.example file not found")
            return
    
    # Try to fix database schema first
    try:
        print("Checking database schema...")
        from fix_database import fix_database
        fix_database()
    except Exception as e:
        print(f"Database fix failed: {e}")
        print("Continuing with application startup...")
    
    # Start the application
    try:
        from run import app
        print("Application starting on http://localhost:5000")
        app.run(debug=True, host='0.0.0.0', port=5000)
    except Exception as e:
        print(f"Failed to start application: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()