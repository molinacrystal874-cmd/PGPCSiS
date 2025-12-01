from webapp import create_app
import os

app = create_app()

if __name__ == '__main__':
    print("Starting PGPCSiS Application...")
    print("Access the application at: http://localhost:5000")
    print("\nDefault login credentials:")
    print("Admin: admin@pgpc.edu / admin123")
    print("Student: TEST001 / student123")
    print("\nPress Ctrl+C to stop the server")
    print("=" * 50)
    
    try:
        app.run(debug=True, host='0.0.0.0', port=5000)
    except KeyboardInterrupt:
        print("\nServer stopped by user")
    except Exception as e:
        print(f"Error starting server: {e}")
        print("Try running: python debug_app.py first")
