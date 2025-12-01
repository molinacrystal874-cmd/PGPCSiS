from .database import db
from datetime import datetime
import uuid
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import String, Integer, Boolean, DateTime, Text, Numeric, JSON, BigInteger
from sqlalchemy.schema import UniqueConstraint
from flask_login import UserMixin # <--- NEW IMPORT

# Unified User model for staff/admin login
class User(db.Model, UserMixin): # <--- MODIFIED: Inherit UserMixin
    """
    Stores user information for staff/admin accounts.
    Separate from Student model to avoid confusion.
    """
    __tablename__ = 'users'

    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(50), nullable=False, default='staff')  # 'staff' or 'admin'
    name = db.Column(db.String(150), nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<User {self.email} ({self.role})>'

# NOTE: The User class is renamed to Student to better match the 'students' table 
# and the application's focus on student accounts, and to align with the PostgreSQL schema.
class Student(db.Model, UserMixin): # <--- MODIFIED: Inherit UserMixin
    """
    Stores student user information (maps to the 'students' table in the PostgreSQL schema).
    The 'role' column is removed as this model is specifically for students.
    """
    __tablename__ = 'students' # Matches PostgreSQL table name
    
    # Primary Key: UUID used for internal SQLAlchemy linking
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4) 
    
    # Credential/Identity Fields (matches PostgreSQL schema)
    student_id = db.Column(db.String(50), unique=True, nullable=False) # The actual student ID for login
    password_hash = db.Column(db.String(255), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    
    # Other Info
    full_name = db.Column(db.String(150), nullable=False) # Renamed 'name' to 'full_name' for clarity
    program = db.Column(db.String(50))
    section = db.Column(db.String(50))
    department = db.Column(db.String(100))  # Add department field
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # --- NEW COLUMN ADDED TO SUPPORT FORCED PASSWORD CHANGE ---
    password_changed = db.Column(db.Boolean, default=False, nullable=False) 
    # --- END NEW COLUMN ---

    # Relationships: Now links to SurveySession
    sessions = db.relationship('SurveySession', backref='student', lazy='dynamic')
    
    def __repr__(self):
        return f'<Student {self.student_id} ({self.full_name})>'


# --- TEACHER, QUESTION, AND LEGACY EVALUATION ---


# Association table for many-to-many Teacher-Department relationship
teacher_department_association = db.Table('teacher_department_association',
    db.Column('teacher_id', UUID(as_uuid=True), db.ForeignKey('teacher.id'), primary_key=True),
    db.Column('department_id', UUID(as_uuid=True), db.ForeignKey('department.id'), primary_key=True)
)

# Association table for many-to-many Teacher-Section relationship
teacher_section_association = db.Table('teacher_section_association',
    db.Column('teacher_id', UUID(as_uuid=True), db.ForeignKey('teacher.id'), primary_key=True),
    db.Column('section_id', UUID(as_uuid=True), db.ForeignKey('section.id'), primary_key=True)
)

class Department(db.Model):
    __tablename__ = 'department'
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = db.Column(db.String(100), unique=True, nullable=False)

    sections = db.relationship('Section', backref='department', lazy='dynamic')
    teachers = db.relationship('Teacher', secondary=teacher_department_association, back_populates='departments_assigned')

    def __repr__(self):
        return f'<Department {self.name}>'

class Section(db.Model):
    __tablename__ = 'section'
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = db.Column(db.String(50), nullable=False)
    department_id = db.Column(UUID(as_uuid=True), db.ForeignKey('department.id'), nullable=False)

    teachers = db.relationship('Teacher', secondary=teacher_section_association, back_populates='sections_assigned')

    # Add a unique constraint to ensure section names are unique within a department
    __table_args__ = (db.UniqueConstraint('name', 'department_id', name='_section_name_department_uc'),)

    def __repr__(self):
        return f'<Section {self.name} (Dept: {self.department.name})>'


class Teacher(db.Model):
    """Stores information about the teachers/staff to be evaluated."""
    __tablename__ = 'teacher'

    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = db.Column(db.String(150), nullable=False)
    # departments = db.Column(db.Text)  # JSON string for multiple departments - REMOVE
    # sections = db.Column(db.Text)     # JSON string for multiple sections - REMOVE
    
    # New relationships
    departments_assigned = db.relationship('Department', secondary=teacher_department_association, back_populates='teachers')
    sections_assigned = db.relationship('Section', secondary=teacher_section_association, back_populates='teachers')
    
    # Legacy fields for backward compatibility
    department = db.Column(db.String(100))
    section = db.Column(db.String(50))
    email = db.Column(db.String(150), unique=True)
    image_url = db.Column(db.String(255))
    
    # Relationships
    # NOTE: The one-to-many relationship now links to the new Answer table (if used for evaluation)
    # Since your current app logic is based on StudentEvaluation, we keep that mapping for now.
    evaluations = db.relationship('TeacherEvaluation', backref='teacher', lazy='dynamic') 

    def __repr__(self):
        return f'<Teacher {self.name} ({self.section})>'

class Question(db.Model):
    """Stores the specific evaluation questions."""
    __tablename__ = 'question'

    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    survey_id = db.Column(UUID(as_uuid=True), db.ForeignKey('surveys.id'), nullable=True)
    criteria = db.Column(db.String(100), nullable=False)
    text = db.Column(db.String(500), nullable=False)

    def __repr__(self):
        return f'<Question {self.criteria}>'
    


class Survey(db.Model):
    """Stores survey information with title and description."""
    __tablename__ = 'surveys'
    
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    staff_type = db.Column(db.String(50), nullable=False, default='teaching') # 'teaching' or 'non_teaching'
    semester = db.Column(db.String(50))
    is_active = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    questions = db.relationship('Question', backref='survey', lazy='dynamic')
    
    def __repr__(self):
        return f'<Survey {self.title}>'

class SurveyStatus(db.Model):
    """Controls whether the evaluation period is active."""
    __tablename__ = 'survey_status'
    
    id = db.Column(db.Integer, primary_key=True)
    is_active = db.Column(db.Boolean, default=False, nullable=False)
    last_change = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<SurveyStatus Active: {self.is_active}>'

class RankingStatus(db.Model):
    """Tracks whether rankings have been published for students to view."""
    __tablename__ = 'ranking_status'
    
    id = db.Column(db.Integer, primary_key=True)
    is_posted_teaching = db.Column(db.Boolean, default=False, nullable=False)
    is_posted_non_teaching = db.Column(db.Boolean, default=False, nullable=False)
    
    def __repr__(self):
        return f'<RankingStatus Teaching: {self.is_posted_teaching}, Non-Teaching: {self.is_posted_non_teaching}>'

# --- NEW TABLES FOR SURVEY & RESULTS STRUCTURE ---

class SurveySession(db.Model):
    """
    Tracks each time a student submits a survey (maps to survey_sessions table).
    This acts as the link between a student and their set of answers/results.
    """
    __tablename__ = 'survey_sessions' # Matches PostgreSQL table name
    
    # Primary Key: SERIAL in PostgreSQL, so use db.Integer with primary_key=True
    session_id = db.Column(db.Integer, primary_key=True) 

    # Foreign Key: Links to the student who submitted the survey.
    student_uuid = db.Column(UUID(as_uuid=True), db.ForeignKey('students.id'), nullable=False)
    survey_id = db.Column(UUID(as_uuid=True), db.ForeignKey('surveys.id'), nullable=True)
    
    survey_title = db.Column(db.String(150), nullable=False)
    submission_date = db.Column(db.DateTime, default=datetime.utcnow)
    is_submitted = db.Column(db.Boolean, default=True)

    # Relationships
    answers = db.relationship('Answer', backref='session', lazy='dynamic')
    result = db.relationship('SurveyResult', backref='session', uselist=False, lazy='joined') 
    
    def __repr__(self):
        return f'<Session {self.session_id} by {self.student_uuid}>'


class Answer(db.Model):
    """
    Stores the detailed, raw answers for each question (maps to answers table).
    NOTE: This replaces the legacy StudentEvaluation table's function for raw data storage.
    """
    __tablename__ = 'answers' # Matches PostgreSQL table name
    
    answer_id = db.Column(db.BigInteger, primary_key=True)

    # Foreign Key: Links this answer back to the specific submission session.
    session_id = db.Column(db.Integer, db.ForeignKey('survey_sessions.session_id'), nullable=False)

    # Identifier for the question (UUID from the Question model)
    question_identifier = db.Column(UUID(as_uuid=True), db.ForeignKey('question.id'), nullable=False)

    # The actual value/response from the student
    response_value = db.Column(db.Text) # Storing the score as text/string
    survey_id = db.Column(UUID(as_uuid=True), db.ForeignKey('surveys.id'), nullable=True)
    
    # Unique constraint ensures a question is only answered once per session
    __table_args__ = (UniqueConstraint('session_id', 'question_identifier', name='_session_question_uc'),)
    
    def __repr__(self):
        return f'<Answer {self.answer_id} for Session {self.session_id}>'


class SurveyResult(db.Model):
    """
    Stores the final, processed, and calculated results (maps to survey_results table).
    """
    __tablename__ = 'survey_results' # Matches PostgreSQL table name
    
    result_id = db.Column(db.Integer, primary_key=True)

    # Foreign Key: Links the result back to the submission session (unique per session).
    session_id = db.Column(db.Integer, db.ForeignKey('survey_sessions.session_id'), unique=True, nullable=False)

    overall_score = db.Column(db.Numeric(5, 2))
    staff_type = db.Column(db.String(50))  # 'teaching' or 'non_teaching'
    
    # Uses JSONB for flexible storage of categorized data analysis
    category_analysis = db.Column(db.JSON) 

    generated_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<Result {self.result_id} for Session {self.session_id}>'


# --- LEGACY TABLE RE-MAPPING (Temporary/For compatibility) ---
# NOTE: Your app.py still uses this table name for compatibility with existing logic.
# This model will need to be refactored or deleted later if you move all data 
# storage to the new Answer table. For now, we rename it and ensure it links.
class TeacherEvaluation(db.Model):
    """
    Stores a single score for one question for one teacher by one student.
    This is based on the legacy 'student_evaluation' table.
    """
    __tablename__ = 'teacher_evaluation'

    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    # The student ID and other UUID foreign keys remain for compatibility with existing app logic
    student_id = db.Column(UUID(as_uuid=True), db.ForeignKey('students.id'), nullable=False)
    teacher_id = db.Column(UUID(as_uuid=True), db.ForeignKey('teacher.id'), nullable=False)
    question_id = db.Column(UUID(as_uuid=True), db.ForeignKey('question.id'), nullable=False)
    survey_id = db.Column(UUID(as_uuid=True), db.ForeignKey('surveys.id'), nullable=True)
    score = db.Column(db.Integer, nullable=False) # 1 to 5
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    # Ensures a student only evaluates a specific teacher once per question per survey period
    __table_args__ = (db.UniqueConstraint('student_id', 'teacher_id', 'question_id', 'survey_id', name='_student_teacher_question_survey_uc'),)
    
    def __repr__(self):
        return f'<TeacherEvaluation {self.student_id} -> {self.teacher_id} Score: {self.score}>'

class StudentComment(db.Model):
    """
    Stores optional comments and suggestions from students.
    """
    __tablename__ = 'student_comments'
    
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = db.Column(db.Integer, db.ForeignKey('survey_sessions.session_id'), nullable=False)
    teacher_id = db.Column(UUID(as_uuid=True), db.ForeignKey('teacher.id'), nullable=False)
    comment_text = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    session = db.relationship('SurveySession', backref='comments')
    teacher = db.relationship('Teacher', backref='student_comments')
    
    def __repr__(self):
        return f'<StudentComment {self.id} for Teacher {self.teacher_id}>'