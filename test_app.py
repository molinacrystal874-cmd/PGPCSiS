#!/usr/bin/env python3
"""
Quick test script to run the app and see errors
"""

from webapp import create_app

if __name__ == '__main__':
    try:
        app = create_app()
        print("App created successfully!")
        app.run(debug=True, host='127.0.0.1', port=5000)
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()