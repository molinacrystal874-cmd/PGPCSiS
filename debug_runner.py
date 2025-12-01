from webapp import create_app
from webapp.models import db
from check_student_teachers import populate_db
import logging
import io

def run_student_home_test():
    app = create_app('testing')
    with app.app_context():
        populate_db(db)

        # Set up logging to capture output
        log_capture_string = io.StringIO()
        ch = logging.StreamHandler(log_capture_string)
        ch.setLevel(logging.INFO)
        logging.getLogger().addHandler(ch)

        with app.test_client() as client:
            # Log in as the student
            client.post('/login', data={
                'email': 'crystalyn079@gmail.com',
                'password': 'studentpass'
            }, follow_redirects=True)

            # Access the student home page
            client.get('/student/home')

        # Get the captured log output
        log_contents = log_capture_string.getvalue()
        log_capture_string.close()

        # Print the logs for debugging
        print("Captured Logs:\n", log_contents)

if __name__ == '__main__':
    run_student_home_test()
