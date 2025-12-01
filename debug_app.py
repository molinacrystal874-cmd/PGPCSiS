import traceback
import sys
import os

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    print("Starting debug mode...")
    from webapp import create_app
    
    print("Creating app...")
    app = create_app()
    
    print("App created successfully!")
    print("Starting server on http://localhost:5000")
    
    app.run(debug=True, host='127.0.0.1', port=5000)
    
except Exception as e:
    print(f"ERROR: {e}")
    print("\nFull traceback:")
    traceback.print_exc()
    input("Press Enter to exit...")