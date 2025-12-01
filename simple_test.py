
import unittest
import uuid
from webapp import create_app, db
from webapp.models import Student, Teacher, Department, Section, User
from werkzeug.security import generate_password_hash

class StudentDashboardTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app('testing')
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()
        self.client = self.app.test_client()

        # Create a department
        self.department = Department(name='BSCS')
        db.session.add(self.department)
        db.session.commit()

        # Create a section
        self.section = Section(name='4A', department_id=self.department.id)
        db.session.add(self.section)
        db.session.commit()

        # Create a teacher
        self.teacher = Teacher(name='Mr. Smith', email='mr.smith@test.com')
        self.teacher.departments_assigned.append(self.department)
        self.teacher.sections_assigned.append(self.section)
        db.session.add(self.teacher)
        db.session.commit()

        # Create a student
        self.student = Student(
            student_id='TEST001',
            full_name='Test Student',
            email='test.student@test.com',
            program='BSCS',
            section='4A',
            password_hash=generate_password_hash('password')
        )
        db.session.add(self.student)
        db.session.commit()
        
        # Create a user for login
        self.user = User(
            id=self.student.id,
            email=self.student.email,
            password_hash=self.student.password_hash,
            role='student',
            name=self.student.full_name
        )
        db.session.add(self.user)
        db.session.commit()


    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_teacher_visible_on_dashboard(self):
        # Login as the student
        with self.client:
            self.client.post('/login', data={
                'role': 'student',
                'student_id': 'TEST001',
                'password': 'password'
            }, follow_redirects=True)

            # Access the student dashboard
            response = self.client.get('/student/home', follow_redirects=True)
            self.assertEqual(response.status_code, 200)
            self.assertIn(b'Mr. Smith', response.data)

if __name__ == '__main__':
    unittest.main()
