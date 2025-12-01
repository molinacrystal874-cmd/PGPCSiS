
import os
import csv
from flask.cli import with_appcontext
import click
from werkzeug.security import generate_password_hash
from webapp import create_app, db
from webapp.models import (
    User, Student, Teacher, Question, TeacherEvaluation, 
    SurveyStatus, Survey, SurveySession, Answer, SurveyResult, RankingStatus,
    Department, Section
)
from datetime import datetime
import json

app = create_app(os.getenv('FLASK_CONFIG') or 'default')

def create_student_list(file_path=None):
    DEFAULT_STUDENT_PASS = 'studentpass'
    hashed_pass = generate_password_hash(DEFAULT_STUDENT_PASS, method='pbkdf2:sha256')

    student_data = []

    if not file_path:
        package_dir = os.path.join(os.path.dirname(__file__), 'webapp', 'data')
        file_path = os.path.join(package_dir, 'students_data.csv')
    else:
        if not os.path.isabs(file_path):
            file_path = os.path.join(os.path.dirname(__file__), file_path)

    if not os.path.exists(file_path):
        print(f"WARNING: Bulk student data file '{file_path}' not found. Loading only essential test user.")
        return [
            {
                'full_name': 'Ma.Crystalyn Molina',
                'email': 'crystalyn079@gmail.com',
                'student_id': 'P202400920',
                'program': 'BSCS',
                'section': 'BSCS-2A',
                'password_hash': hashed_pass,
                'password_changed': True # CRITICAL FIX: Set to True
            }
        ]

    try:
        with open(file_path, mode='r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            for row in reader:
                row['password_hash'] = hashed_pass
                row['password_changed'] = False
                student_data.append(row)

        return student_data

    except Exception as e:
        print(f"ERROR reading student CSV ({file_path}): {e}")
        return []

@click.command('init-db')
@with_appcontext
def init_db_command():
    """Initializes the database."""
    db.drop_all()
    db.create_all()

    if SurveyStatus.query.get(1) is None: 
        db.session.add(SurveyStatus(id=1, is_active=False, last_change=datetime.utcnow()))
        db.session.commit()
        print("Database: Survey Status initialized.")

    try:
        if Survey.query.count() == 0:
            # Add a survey for teaching staff
            teaching_survey = Survey(
                title='Teacher Evaluation 2024',
                description='Annual teacher performance evaluation survey',
                staff_type='teaching'  # Explicitly set staff_type
            )
            db.session.add(teaching_survey)
            db.session.flush() # Flush to get the ID for the questions

            # Add a survey for non-teaching staff
            non_teaching_survey = Survey(
                title='Non-Teaching Staff Evaluation 2024',
                description='Annual non-teaching staff performance evaluation',
                staff_type='non_teaching' # Explicitly set staff_type
            )
            db.session.add(non_teaching_survey)
            db.session.flush()

            # Define questions for both surveys
            mock_questions = [
                # Teaching questions
                Question(criteria='Teaching', text='Instructor is knowledgeable about the subject matter.', survey_id=teaching_survey.id),
                Question(criteria='Communication', text='The teacher communicates expectations clearly.', survey_id=teaching_survey.id),
                
                # Non-teaching questions
                Question(criteria='Professionalism', text='The staff member adheres to college policies.', survey_id=non_teaching_survey.id),
                Question(criteria='Efficiency', text='The staff member completes tasks in a timely manner.', survey_id=non_teaching_survey.id)
            ]
            db.session.add_all(mock_questions)
            db.session.commit()
            print("Database: Default surveys and questions loaded.")
    except Exception as e:
        db.session.rollback()  # Rollback the session to allow further queries
        print(f"Database: Error initializing surveys/questions: {e}")
        
        # Fallback data loading
        try:
            if Question.query.count() == 0:
                mock_questions = [
                    Question(criteria='Teaching', text='Instructor is knowledgeable about the subject matter.'),
                    Question(criteria='Professionalism', text='The staff member adheres to college policies.'),
                    Question(criteria='Communication', text='The teacher communicates expectations clearly.')
                ]
                db.session.add_all(mock_questions)
                db.session.commit()
                print("Database: Mock question data loaded (fallback mode).")
        except Exception as e2:
            print(f"Database: Error in fallback question initialization: {e2}")
        
    if Teacher.query.count() == 0:
        # Create Departments
        bscs_dept = Department(name='BSCS')
        bsma_dept = Department(name='BSMA')
        bpa_dept = Department(name='BPA')
        bscrim_dept = Department(name='BSCRIM')
        admin_dept = Department(name='Admin')
        db.session.add_all([bscs_dept, bsma_dept, bpa_dept, bscrim_dept, admin_dept])
        db.session.commit()

        # Create Sections
        bscs_1a = Section(name='BSCS-1A', department_id=bscs_dept.id)
        bscs_2a = Section(name='BSCS-2A', department_id=bscs_dept.id)
        bsma_1b = Section(name='BSMA-1B', department_id=bsma_dept.id)
        admin_office = Section(name='Admin-Office', department_id=admin_dept.id)
        db.session.add_all([bscs_1a, bscs_2a, bsma_1b, admin_office])
        db.session.commit()

        mock_teachers = [
            Teacher(name="Prof. Cruz", email="pcruz@pgpc.edu", image_url="https://placehold.co/100x100/5070ff/ffffff?text=PC"),
            Teacher(name="Ms. Garcia", email="mgarcia@pgpc.edu", image_url="https://placehold.co/100x100/39b788/ffffff?text=MG"),
            Teacher(name="Dr. Smith", email="dsmith@pgpc.edu", image_url="https://placehold.co/100x100/ff7050/ffffff?text=DS"),
            Teacher(name="Engr. Reyes", email="ereyes@pgpc.edu", image_url="https://placehold.co/100x100/50aaff/ffffff?text=ER"),
            Teacher(name="Dr. Reyes", email="dreyes@pgpc.edu", image_url="https://placehold.co/100x100/d9534f/ffffff?text=DR"),
            Teacher(name="Dean Alva", email="calva@pgpc.edu", image_url="https://placehold.co/100x100/222222/ffffff?text=DA"),
        ]
        db.session.add_all(mock_teachers)
        db.session.commit()

        # Assign teachers to departments and sections
        mock_teachers[0].departments_assigned.append(bscs_dept)
        mock_teachers[0].sections_assigned.append(bscs_1a)
        mock_teachers[1].departments_assigned.append(bscs_dept)
        mock_teachers[1].sections_assigned.append(bscs_1a)
        mock_teachers[2].departments_assigned.append(bscs_dept)
        mock_teachers[2].sections_assigned.append(bscs_2a)
        mock_teachers[3].departments_assigned.append(bscs_dept)
        mock_teachers[3].sections_assigned.append(bscs_2a)
        mock_teachers[4].departments_assigned.append(bsma_dept)
        mock_teachers[4].sections_assigned.append(bsma_1b)
        mock_teachers[5].departments_assigned.append(admin_dept)
        mock_teachers[5].sections_assigned.append(admin_office)

        db.session.commit()
        print("Database: Mock teacher data loaded.")

    if Student.query.count() == 0:
        student_list = create_student_list()
        students_to_add = []
        
        for data in student_list:
            students_to_add.append(Student(
                full_name=data['full_name'],
                email=data['email'],
                password_hash=data['password_hash'],
                student_id=data['student_id'],
                program=data['program'],
                section=data['section'],
                department=data.get('department', data['program']),
                password_changed=data.get('password_changed', False)
            ))
        
        db.session.add_all(students_to_add)
        db.session.commit()
        print(f"Database: {len(student_list)} student accounts loaded.")

    if User.query.count() == 0:
        admin_user = User(
            name='Admin User',
            email='admin@pgpc.edu',
            password_hash=generate_password_hash('adminpass', method='pbkdf2:sha256'),
            role='staff'
        )
        db.session.add(admin_user)
        db.session.commit()
        print("Database: Admin user created.")
    
    print("Database initialization complete.")

app.cli.add_command(init_db_command)

if __name__ == '__main__':
    init_db_command()
