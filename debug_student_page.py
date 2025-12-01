
import unittest
from webapp import create_app
from webapp.models import db, Student, Teacher, Section, Department
import logging
import io

class StudentPageTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app('testing')
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()
        self.client = self.app.test_client()

        # Create a test student
        student = Student(full_name='Test Student', student_id='TEST001', program='BSCS', section='A', email='test@student.com', password='password')
        db.session.add(student)

        # Create a test teacher
        department = Department(name='BSCS')
        db.session.add(department)
        db.session.commit()

        section = Section(name='A', department_id=department.id)
        db.session.add(section)
        db.session.commit()

        teacher = Teacher(name='Test Teacher', email='test@teacher.com')
        teacher.departments_assigned.append(department)
        teacher.sections_assigned.append(section)
        db.session.add(teacher)

        db.session.commit()

        self.student_id = student.id

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_student_home_page_logs(self):
        # Set up logging to capture output
        log_capture_string = io.StringIO()
        ch = logging.StreamHandler(log_capture_string)
        ch.setLevel(logging.INFO)
        logging.getLogger().addHandler(ch)

        # Log in as the student
        with self.client:
            self.client.post('/login', data=dict(
                email='test@student.com',
                password='password'
            ), follow_redirects=True)

            # Access the student home page
            response = self.client.get('/student/home')
            self.assertEqual(response.status_code, 200)

        # Get the captured log output
        log_contents = log_capture_string.getvalue()
        log_capture_string.close()

        # Print the logs for debugging
        print("Captured Logs:\n", log_contents)

        # Assert that the logs contain the expected information
        self.assertIn("Fetching teachers for student", log_contents)
        self.assertIn("in program 'BSCS' and section 'A'", log_contents)
        self.assertIn("Found 1 teachers.", log_contents)

if __name__ == '__main__':
    test = StudentPageTestCase()
    test.setUp()
    test.test_student_home_page_logs()
    test.tearDown()

