
import os
import csv
from webapp import create_app, db
from webapp.models import Student, Teacher, Department, Section, Survey, Question, SurveyStatus, User
from werkzeug.security import generate_password_hash
from datetime import datetime

def populate_db(db):
    """Populates the database with test data."""
    db.drop_all()
    db.create_all()

    if SurveyStatus.query.get(1) is None:
        db.session.add(SurveyStatus(id=1, is_active=False, last_change=datetime.utcnow()))
        db.session.commit()

    if Survey.query.count() == 0:
        teaching_survey = Survey(
            title='Teacher Evaluation 2024',
            description='Annual teacher performance evaluation survey',
            staff_type='teaching'
        )
        db.session.add(teaching_survey)
        db.session.flush()

        non_teaching_survey = Survey(
            title='Non-Teaching Staff Evaluation 2024',
            description='Annual non-teaching staff performance evaluation',
            staff_type='non_teaching'
        )
        db.session.add(non_teaching_survey)
        db.session.flush()

        mock_questions = [
            Question(criteria='Teaching', text='Instructor is knowledgeable about the subject matter.', survey_id=teaching_survey.id),
            Question(criteria='Communication', text='The teacher communicates expectations clearly.', survey_id=teaching_survey.id),
            Question(criteria='Professionalism', text='The staff member adheres to college policies.', survey_id=non_teaching_survey.id),
            Question(criteria='Efficiency', text='The staff member completes tasks in a timely manner.', survey_id=non_teaching_survey.id)
        ]
        db.session.add_all(mock_questions)
        db.session.commit()

    if Teacher.query.count() == 0:
        # Create departments and sections
        bscs_dept = Department(name='BSCS')
        bsma_dept = Department(name='BSMA')
        admin_dept = Department(name='Admin')
        db.session.add_all([bscs_dept, bsma_dept, admin_dept])
        db.session.commit()

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


    if Student.query.count() == 0:
        hashed_pass = generate_password_hash('studentpass', method='pbkdf2:sha256')
        student_list = [
            {
                'full_name': 'Ma.Crystalyn Molina',
                'email': 'crystalyn079@gmail.com',
                'student_id': 'P202400920',
                'program': 'BSCS',
                'section': 'BSCS-2A',
                'password_hash': hashed_pass,
                'password_changed': True
            }
        ]
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

    if User.query.count() == 0:
        admin_user = User(
            name='Admin User',
            email='admin@pgpc.edu',
            password_hash=generate_password_hash('adminpass', method='pbkdf2:sha256'),
            role='staff'
        )
        db.session.add(admin_user)
        db.session.commit()


def run_test():
    app = create_app('testing')
    with app.app_context():
        populate_db(db)

        # Get the test student
        student = Student.query.filter_by(student_id='P202400920').first()

        # Get the teachers for the student
        teachers_list = Teacher.query.join(Teacher.departments_assigned).join(Teacher.sections_assigned).filter(
            db.func.lower(Department.name) == student.program.lower(),
            db.func.lower(Section.name) == student.section.lower()
        ).distinct().all()

        print(f"Student: {student.full_name}")
        print(f"Program: {student.program}")
        print(f"Section: {student.section}")
        print(f"Found {len(teachers_list)} teachers:")
        for teacher in teachers_list:
            print(f"  - {teacher.name}")

if __name__ == '__main__':
    run_test()
