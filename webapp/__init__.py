from flask import Flask
import os
from datetime import datetime
from werkzeug.security import generate_password_hash
from .database import db 
# webapp/__init__.py, Line 6 (The problematic line)
# OLD: from .models import User, Student, Teacher, Question, TeacherEvaluation, SurveyStatus, Survey
# NEW:
from .models import (
    User, Student, Teacher, Question, TeacherEvaluation, 
    SurveyStatus, Survey, SurveySession, Answer, SurveyResult, RankingStatus
)
import csv 
from dotenv import load_dotenv  
from flask_login import LoginManager 
from sqlalchemy import text
from flask_mail import Mail
import logging # Added logging import

# Configure basic logging to ensure errors are printed
logging.basicConfig(level=logging.DEBUG)

load_dotenv()

# Initialize Mail object
mail = Mail()

POSTGRES_USER = os.getenv('POSTGRES_USER', 'postgres')
POSTGRES_PASS = os.getenv('POSTGRES_PASS', '022006')
POSTGRES_DB = os.getenv('POSTGRES_DB', 'pgpc_sis_db')
POSTGRES_HOST = os.getenv('POSTGRES_HOST', 'localhost')
POSTGRES_PORT = os.getenv('POSTGRES_PORT', '5432')

def create_student_list(file_path=None):
    DEFAULT_STUDENT_PASS = 'studentpass'
    hashed_pass = generate_password_hash(DEFAULT_STUDENT_PASS, method='pbkdf2:sha256')

    student_data = []

    if not file_path:
        package_dir = os.path.dirname(__file__)
        file_path = os.path.join(package_dir, 'data', 'students_data.csv')
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

def initialize_database(app):
    with app.app_context():
        # Check connection before creating all tables
        try:
            with db.engine.connect() as connection:
                connection.execute(text('SELECT 1'))
            print("Database connection successful during initialization check.")
        except Exception as e:
            print(f"Database connection error during initialization check: {e}")
            print("Continuing with table creation anyway...")

        try:
            # Drop all tables to ensure a clean slate (for development)
            # db.drop_all()
            # print("Database tables dropped successfully.")
            db.create_all()
            print("Database tables created successfully")
        except Exception as e:
            print(f"Error creating tables: {e}")
            return

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
            import json
            mock_teachers = [
                Teacher(name="Prof. Cruz", department="BSCS", section="BSCS-1A", 
                       departments=json.dumps(["BSCS"]), sections=json.dumps(["BSCS-1A", "BSCS-1B"]),
                       email="pcruz@pgpc.edu", image_url="https://placehold.co/100x100/5070ff/ffffff?text=PC"),
                Teacher(name="Ms. Garcia", department="BSCS", section="BSCS-1A", 
                       departments=json.dumps(["BSCS"]), sections=json.dumps(["BSCS-1A"]),
                       email="mgarcia@pgpc.edu", image_url="https://placehold.co/100x100/39b788/ffffff?text=MG"),
                Teacher(name="Dr. Smith", department="BSCS", section="BSCS-2A", 
                       departments=json.dumps(["BSCS", "BSMA"]), sections=json.dumps(["BSCS-2A", "BSMA-1A"]),
                       email="dsmith@pgpc.edu", image_url="https://placehold.co/100x100/ff7050/ffffff?text=DS"),
                Teacher(name="Engr. Reyes", department="BSCS", section="BSCS-2A", 
                       departments=json.dumps(["BSCS"]), sections=json.dumps(["BSCS-2A"]),
                       email="ereyes@pgpc.edu", image_url="https://placehold.co/100x100/50aaff/ffffff?text=ER"),
                Teacher(name="Dr. Reyes", department="BSMA", section="BSMA-1B", 
                       departments=json.dumps(["BSMA"]), sections=json.dumps(["BSMA-1B"]),
                       email="dreyes@pgpc.edu", image_url="https://placehold.co/100x100/d9534f/ffffff?text=DR"),
                Teacher(name="Dean Alva", department="Admin", section="Admin-Office", 
                       departments=json.dumps(["Admin"]), sections=json.dumps(["Admin-Office"]),
                       email="calva@pgpc.edu", image_url="https://placehold.co/100x100/222222/ffffff?text=DA"),
            ]
            db.session.add_all(mock_teachers)
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

def create_app():
    app = Flask(__name__)
    
    # Force DEBUG mode ON for troubleshooting
    app.config['DEBUG'] = True
    app.config['TESTING'] = True

    app.secret_key = "40809e68989990d2d506801bfe12c3cffa717cd83d669232408c3c734c7159d5"

    @app.after_request
    def apply_no_cache(response):
        """ 🔐 MODIFIED: Ensure all responses have headers to prevent caching. """
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "-1"
        return response

    app.config.update(
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE='Lax',
        SESSION_COOKIE_SECURE=False
    )
    
    # Use DATABASE_URL from environment (Render provides this) or fallback to local PostgreSQL
    database_url = os.getenv('DATABASE_URL')
    if database_url:
        # Render uses postgres:// but SQLAlchemy needs postgresql://
        if database_url.startswith('postgres://'):
            database_url = database_url.replace('postgres://', 'postgresql://', 1)
        app.config['SQLALCHEMY_DATABASE_URI'] = database_url
        print(f"Using production database: {database_url[:50]}...")
    else:
        # Local development
        postgres_uri = f"postgresql://{POSTGRES_USER}:{POSTGRES_PASS}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"
        sqlite_uri = f"sqlite:///{os.path.join(os.path.dirname(__file__), 'data', 'app.db')}"
        
        app.config['SQLALCHEMY_DATABASE_URI'] = postgres_uri
        
        # Test database connection for local development
        try:
            from sqlalchemy import create_engine
            engine = create_engine(app.config['SQLALCHEMY_DATABASE_URI'])
            with engine.connect() as conn:
                conn.execute(text('SELECT 1'))
            print(f"Database connection successful: {app.config['SQLALCHEMY_DATABASE_URI']}")
        except Exception as e:
            print(f"PostgreSQL connection failed: {e}")
            print("Falling back to SQLite database...")
            app.config['SQLALCHEMY_DATABASE_URI'] = sqlite_uri
            # Ensure data directory exists
            os.makedirs(os.path.join(os.path.dirname(__file__), 'data'), exist_ok=True)
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # Email configuration
    app.config['MAIL_SERVER'] = os.getenv('MAIL_SERVER', 'smtp.gmail.com')
    app.config['MAIL_PORT'] = int(os.getenv('MAIL_PORT', 587))
    app.config['MAIL_USE_TLS'] = os.getenv('MAIL_USE_TLS', 'True').lower() in ('true', '1', 't')
    app.config['MAIL_USE_SSL'] = os.getenv('MAIL_USE_SSL', 'False').lower() in ('true', '1', 't')
    app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')
    app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')
    app.config['MAIL_DEFAULT_SENDER'] = os.getenv('MAIL_USERNAME')
 
    db.init_app(app)
    mail.init_app(app)

    login_manager = LoginManager()
    login_manager.init_app(app)
    
    login_manager.login_view = 'auth.login'
    login_manager.session_protection = "strong" 

    @login_manager.user_loader
    def load_user(user_id):
        # We need to handle potential UUID errors here
        try:
            from uuid import UUID
            user_id_uuid = UUID(user_id)
            
            # Try Student first
            student = Student.query.get(user_id_uuid)
            if student:
                return student
                
            # Then try User
            user = User.query.get(user_id_uuid)
            if user:
                return user
                
        except (ValueError, TypeError) as e:
            print(f"Invalid UUID in session: {user_id}, Error: {e}")
            return None
        except Exception as e:
            print(f"Database error in user_loader: {e}")
            return None
            
        return None

    try:
        from .auth import auth
        from .app import views
        print("Blueprints imported successfully")
    except Exception as e:
        print(f"Blueprint import error: {e}")
        raise e 

    app.register_blueprint(auth, url_prefix='/')
    app.register_blueprint(views, url_prefix='/')
    
    # Debug: Print all registered routes
    print("Registered routes:")
    for rule in app.url_map.iter_rules():
        print(f"  {rule.rule} -> {rule.endpoint} [{', '.join(rule.methods)}]")
    print("End of registered routes")

    @app.context_processor
    def utility_processor():
        return dict(enumerate=enumerate)

    # Add error handlers
    @app.errorhandler(500)
    def internal_error(error):
        print(f"Internal Server Error: {error}")
        import traceback
        traceback.print_exc()
        return "<h1>Internal Server Error</h1><p>Check the console for details.</p>", 500

    @app.errorhandler(404)
    def not_found(error):
        return "<h1>Page Not Found</h1>", 404

    # Add forgot password routes directly to app
    @app.route('/forgot-password', methods=['POST'])
    def forgot_password():
        try:
            data = request.get_json()
            email = data.get('email', '').strip().lower()
            user_type = data.get('user_type', 'student')
            
            if not email:
                return jsonify({'success': False, 'message': 'Email is required'}), 400
            
            user = None
            user_name = None
            
            if user_type == 'staff':
                user = User.query.filter_by(email=email).first()
                if user:
                    user_name = user.name
            else:
                user = Student.query.filter_by(email=email).first()
                if user:
                    user_name = user.full_name
                else:
                    import csv
                    csv_path = os.path.join(os.path.dirname(__file__), 'data', 'students_data.csv')
                    print(f"Looking for CSV at: {csv_path}")
                    print(f"File exists: {os.path.exists(csv_path)}")
                    
                    try:
                        with open(csv_path, 'r', encoding='utf-8') as file:
                            reader = csv.DictReader(file)
                            for row in reader:
                                row_email = row['email'].strip().lower()
                                print(f"Comparing: '{row_email}' == '{email}' = {row_email == email}")
                                if row_email == email:
                                    user_name = row['full_name']
                                    user = type('CSVUser', (), {
                                        'email': email,
                                        'full_name': user_name,
                                        'student_id': row['student_id'],
                                        'is_csv_user': True
                                    })()
                                    print(f"Found CSV user: {user_name}")
                                    break
                    except Exception as e:
                        print(f"Error reading CSV: {e}")
            
            if not user:
                return jsonify({'success': False, 'message': 'Email not found in our records'}), 404
            
            import random
            otp_code = str(random.randint(100000, 999999))
            session[f'reset_otp_{email}'] = otp_code
            session[f'reset_email_{email}'] = email
            session[f'reset_user_type_{email}'] = user_type
            
            return jsonify({
                'success': True, 
                'message': f'Verification code ready for {email}',
                'otp_code': otp_code,
                'user_name': user_name
            }), 200
            
        except Exception as e:
            print(f"Forgot password error: {e}")
            return jsonify({'success': False, 'message': 'An error occurred'}), 500
    
    @app.route('/reset-password', methods=['POST'])
    def reset_password():
        try:
            data = request.get_json()
            email = data.get('email', '').strip().lower()
            otp_code = data.get('otp_code', '').strip()
            new_password = data.get('new_password', '').strip()
            
            if not all([email, otp_code, new_password]):
                return jsonify({'success': False, 'message': 'All fields are required'}), 400
            
            if len(new_password) < 6:
                return jsonify({'success': False, 'message': 'Password must be at least 6 characters'}), 400
            
            stored_otp = session.get(f'reset_otp_{email}')
            if not stored_otp or str(stored_otp) != str(otp_code):
                return jsonify({'success': False, 'message': 'Invalid verification code'}), 400
            
            user_type = session.get(f'reset_user_type_{email}', 'student')
            
            if user_type == 'staff':
                user = User.query.filter_by(email=email).first()
                if user:
                    user.password_hash = generate_password_hash(new_password, method='pbkdf2:sha256')
                    db.session.commit()
                else:
                    return jsonify({'success': False, 'message': 'User not found'}), 404
            else:
                user = Student.query.filter_by(email=email).first()
                if user:
                    user.password_hash = generate_password_hash(new_password, method='pbkdf2:sha256')
                    user.password_changed = True
                    db.session.commit()
                else:
                    import csv
                    csv_path = os.path.join(os.path.dirname(__file__), 'data', 'students_data.csv')
                    student_found = False
                    try:
                        with open(csv_path, 'r', encoding='utf-8') as file:
                            reader = csv.DictReader(file)
                            for row in reader:
                                if row['email'].strip().lower() == email:
                                    new_student = Student(
                                        full_name=row['full_name'],
                                        email=email,
                                        password_hash=generate_password_hash(new_password, method='pbkdf2:sha256'),
                                        student_id=row['student_id'],
                                        program=row['program'],
                                        section=row['section'],
                                        password_changed=True
                                    )
                                    db.session.add(new_student)
                                    db.session.commit()
                                    student_found = True
                                    break
                    except Exception as e:
                        print(f"Error reading CSV for reset: {e}")
                    
                    if not student_found:
                        return jsonify({'success': False, 'message': 'Student not found'}), 404
            
            session.pop(f'reset_otp_{email}', None)
            session.pop(f'reset_email_{email}', None)
            session.pop(f'reset_user_type_{email}', None)
            
            return jsonify({'success': True, 'message': 'Password updated successfully'}), 200
            
        except Exception as e:
            db.session.rollback()
            print(f"Reset password error: {e}")
            return jsonify({'success': False, 'message': 'An error occurred while updating password'}), 500

    with app.app_context():
        try:
            initialize_database(app)
        except Exception as e:
            print(f"Database initialization error: {e}")
            import traceback
            traceback.print_exc()

    return app

if __name__ == '__main__':
    # Flask will automatically use the DEBUG=True configured above
    app = create_app()
    app.run()