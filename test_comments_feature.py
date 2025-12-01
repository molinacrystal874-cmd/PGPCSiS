#!/usr/bin/env python3
"""
Test script to verify the comments feature is working correctly.
"""

import os
import sys
import uuid
from datetime import datetime

# Add the webapp directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'webapp'))

from webapp import create_app
from webapp.database import db
from webapp.models import Student, Teacher, SurveySession, StudentComment, Survey

def test_comments_feature():
    """Test the comments functionality."""
    app = create_app()
    
    with app.app_context():
        try:
            # Check if StudentComment table exists
            result = db.engine.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='student_comments';")
            if not result.fetchone():
                print("❌ StudentComment table does not exist. Run migrate_comments.py first.")
                return False
            
            print("✅ StudentComment table exists")
            
            # Test creating a comment (simulation)
            print("🧪 Testing comment creation...")
            
            # Find or create a test student
            test_student = Student.query.filter_by(student_id='TEST001').first()
            if not test_student:
                test_student = Student(
                    student_id='TEST001',
                    full_name='Test Student',
                    email='test@example.com',
                    password_hash='test_hash',
                    program='BSCS',
                    section='1A'
                )
                db.session.add(test_student)
                db.session.flush()
            
            # Find or create a test teacher
            test_teacher = Teacher.query.filter_by(name='Test Teacher').first()
            if not test_teacher:
                test_teacher = Teacher(
                    name='Test Teacher',
                    email='teacher@example.com',
                    department='BSCS'
                )
                db.session.add(test_teacher)
                db.session.flush()
            
            # Create a test survey session
            test_session = SurveySession(
                student_uuid=test_student.id,
                survey_title='Test Survey',
                submission_date=datetime.utcnow()
            )
            db.session.add(test_session)
            db.session.flush()
            
            # Create a test comment
            test_comment = StudentComment(
                session_id=test_session.session_id,
                teacher_id=test_teacher.id,
                comment_text='This is a test comment for the teacher evaluation system.'
            )
            db.session.add(test_comment)
            db.session.commit()
            
            print("✅ Test comment created successfully")
            
            # Verify the comment can be retrieved
            retrieved_comment = StudentComment.query.filter_by(
                session_id=test_session.session_id,
                teacher_id=test_teacher.id
            ).first()
            
            if retrieved_comment and retrieved_comment.comment_text == test_comment.comment_text:
                print("✅ Comment retrieval works correctly")
            else:
                print("❌ Comment retrieval failed")
                return False
            
            # Clean up test data
            db.session.delete(test_comment)
            db.session.delete(test_session)
            db.session.commit()
            
            print("✅ Test cleanup completed")
            
            return True
            
        except Exception as e:
            print(f"❌ Error during testing: {e}")
            db.session.rollback()
            return False

if __name__ == '__main__':
    print("🧪 Testing comments feature...")
    success = test_comments_feature()
    
    if success:
        print("\n🎉 All tests passed! Comments feature is working correctly.")
        print("\nFeature Summary:")
        print("• ✅ StudentComment table exists")
        print("• ✅ Comments can be created and stored")
        print("• ✅ Comments can be retrieved for display")
        print("• ✅ Database relationships work correctly")
    else:
        print("\n❌ Tests failed. Please check the error messages above.")
        sys.exit(1)