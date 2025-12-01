#!/usr/bin/env python3
"""
Migration script to ensure StudentComment table exists in the database.
Run this script to add the comments functionality to existing databases.
"""

import os
import sys

# Add the webapp directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'webapp'))

from webapp import create_app
from webapp.database import db
from webapp.models import StudentComment

def migrate_comments():
    """Create the StudentComment table if it doesn't exist."""
    app = create_app()
    
    with app.app_context():
        try:
            # Create all tables (this will only create missing ones)
            db.create_all()
            print("✅ StudentComment table created successfully!")
            print("📝 Students can now submit optional comments with their evaluations.")
            print("📊 Admins can generate individual staff reports that include comments.")
            
        except Exception as e:
            print(f"❌ Error creating StudentComment table: {e}")
            return False
    
    return True

if __name__ == '__main__':
    print("🔄 Migrating database to add comments functionality...")
    success = migrate_comments()
    
    if success:
        print("\n🎉 Migration completed successfully!")
        print("\nNew Features Added:")
        print("• Students can now leave optional comments for each staff member")
        print("• Comments are saved with evaluation submissions")
        print("• Individual staff reports now include student comments")
        print("• Comments appear in review mode for students")
    else:
        print("\n❌ Migration failed. Please check the error messages above.")
        sys.exit(1)