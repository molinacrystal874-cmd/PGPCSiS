# webapp/app.py
from flask import Blueprint, render_template, session, redirect, url_for, flash, request, jsonify, make_response, current_app, send_from_directory
from .models import db, Student, Teacher, Question, TeacherEvaluation, SurveyStatus, SurveySession, Answer, SurveyResult, Survey, RankingStatus, Section, Department, StudentComment
from sqlalchemy import func, text, inspect
from functools import wraps
from datetime import datetime
from reportlab.lib.pagesizes import letter, landscape
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib import colors
from io import BytesIO
import os
import uuid
import json 
import traceback 
import logging
from flask_mail import Message
from . import mail
from reportlab.lib.styles import getSampleStyleSheet

# In app.py
# Set up logger for this module
logger = logging.getLogger(__name__)

# Initialize the Blueprint
views = Blueprint('views', __name__) 

# --- Decorators ---

def is_logged_in():
    """Return True when a user_id is present in the session."""
    return 'user_id' in session

def login_required(f):
    """Decorator that ensures the user is logged in and prevents caching."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not is_logged_in():
            flash('Please log in to access this page.', 'error')
            return redirect(url_for('auth.login'))
        
        # Create a response from the view function's result
        result = f(*args, **kwargs)
        response = make_response(result)

        # 🔐 FIX: Forcefully apply no-cache headers here to prevent back-button issues.
        response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '-1'
        
        return response
    return decorated_function

def admin_required(f):
    """Decorator that ensures the user is logged in and has the 'staff' role."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Check for login and role first
        if not is_logged_in():
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'status': 'error', 'message': 'Authentication required. Please log in.'}), 401
            flash('Please log in to access this page.', 'error')
            return redirect(url_for('auth.login'))
            
        if session.get('user_role') != 'staff':
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'status': 'error', 'message': 'Admin access required.'}), 403
            flash('Admin access required.', 'error')
            return redirect(url_for('auth.login'))
        
        return f(*args, **kwargs)
    return decorated_function

# -----------------------------------------------------------------
# --- UTILITY/CALCULATION LOGIC ---
# -----------------------------------------------------------------

def calculate_non_teaching_staff_averages():
    """Calculates the average score and count of evaluations for non-teaching staff."""
    try:
        # This assumes non-teaching staff are identified by a specific department like 'Admin'
        # and that they are stored in the same Teacher model.
        # This logic will need to be adjusted if you have a separate NonTeachingStaff model.
        non_teaching_staff_list = Teacher.query.options(
            db.joinedload(Teacher.departments_assigned),
            db.joinedload(Teacher.sections_assigned)
        ).join(Teacher.departments_assigned).filter(
            Department.name == 'Admin'
        ).all()
        
        if not non_teaching_staff_list:
            logger.debug("No non-teaching staff found with 'Admin' department.")
            return []

        non_teaching_staff_ids = {str(staff.id) for staff in non_teaching_staff_list}
        
        # Use the same calculation logic as for teachers
        sums, counts = {}, {}
        answers = Answer.query.filter(Answer.response_value.like('%|%')).all()

        for ans in answers:
            try:
                score_str, entity_id = ans.response_value.split('|', 1)
                if entity_id in non_teaching_staff_ids:
                    score = float(score_str)
                    sums[entity_id] = sums.get(entity_id, 0.0) + score
                    counts[entity_id] = counts.get(entity_id, 0) + 1
            except (ValueError, IndexError) as e:
                logger.warning(f"Skipping malformed answer for non-teaching staff: {ans.response_value}, Error: {e}")
                continue

        results = []
        for staff in non_teaching_staff_list:
            staff_id_str = str(staff.id)
            cnt = counts.get(staff_id_str, 0)
            avg = (sums.get(staff_id_str, 0.0) / cnt) if cnt > 0 else 0.0
            
            departments_assigned_names = [d.name for d in staff.departments_assigned]
            sections_assigned_names = [s.name for s in staff.sections_assigned]
            
            results.append({
                'id': staff.id, 
                'name': staff.name, 
                'department': ', '.join(departments_assigned_names) if departments_assigned_names else 'Admin',
                'section': ', '.join(sections_assigned_names) if sections_assigned_names else 'N/A', 
                'score': round(avg, 2), 
                'count': cnt
            })

        results.sort(key=lambda x: x['score'], reverse=True)
        return results
    except Exception as e:
        logger.error(f"Critical error in calculate_non_teaching_staff_averages: {e}")
        return []

def calculate_teacher_averages():
    """Calculates the average score and count of evaluations for each teacher.
    Returns results sorted by highest score first (Rank 1 = Highest Score)."""
    try:
        sums = {}
        counts = {}

        try:
            answers = Answer.query.filter(Answer.response_value.like('%|%')).all()
        except Exception as e:
            logger.error(f"Error fetching answers: {e}")
            return []
        
        if not answers:
            logger.debug("No evaluation data found in Answer table.")
            return []
        
        for ans in answers:
            try:
                # Handle both old format (score|teacher) and new format (score|teacher;score|teacher)
                teacher_scores = ans.response_value.split(';')
                
                for teacher_score in teacher_scores:
                    parts = teacher_score.split('|')
                    if len(parts) >= 2:
                        score_str = parts[0]
                        teacher_uuid = parts[1]
                        score = float(score_str)
                        
                        sums[teacher_uuid] = sums.get(teacher_uuid, 0.0) + score
                        counts[teacher_uuid] = counts.get(teacher_uuid, 0) + 1
            except Exception as e:
                logger.warning(f"Error processing answer ID {getattr(ans, 'answer_id', 'N/A')}: {e}")
                continue

        results = []
        try:
            teachers = Teacher.query.options(
                db.joinedload(Teacher.departments_assigned),
                db.joinedload(Teacher.sections_assigned)
            ).all()
            teachers_map = {str(t.id): t for t in teachers}
        except Exception as e:
            logger.error(f"Error fetching teachers: {e}")
            return []
        
        for t_id, t in teachers_map.items():
            try:
                cnt = counts.get(t_id, 0)
                avg = (sums.get(t_id, 0.0) / cnt) if cnt > 0 else 0.0
                
                # Use new relationships for departments and sections
                departments_assigned_names = [d.name for d in t.departments_assigned]
                sections_assigned_names = [s.name for s in t.sections_assigned]
                
                results.append({
                    'id': t.id,
                    'name': t.name,
                    'department': ', '.join(departments_assigned_names) if departments_assigned_names else 'N/A',
                    'section': ', '.join(sections_assigned_names) if sections_assigned_names else 'N/A',
                    'score': round(avg, 2),
                    'count': cnt
                })
            except Exception as e:
                logger.error(f"Error processing teacher {t_id}: {e}")
                continue

        results.sort(key=lambda x: x['score'], reverse=True)
        return results
        
    except Exception as e:
        logger.error(f"Critical error in calculate_teacher_averages: {e}")
        return []

def calculate_program_reports(programs):
    """
    Calculates evaluation averages for teachers, grouped by program.
    """
    program_reports = {}
    
    try:
        # Get all evaluation answers first to avoid re-querying in a loop
        sums = {}
        counts = {}
        answers = Answer.query.filter(Answer.response_value.like('%|%')).all()
        for ans in answers:
            try:
                score_str, teacher_uuid = ans.response_value.split('|', 1)
                score = float(score_str)
                sums[teacher_uuid] = sums.get(teacher_uuid, 0.0) + score
                counts[teacher_uuid] = counts.get(teacher_uuid, 0) + 1
            except (ValueError, IndexError):
                continue

        for program_code in programs:
            if program_code == 'Admin':
                continue

            # Find teachers belonging to this program
            # The `departments` column is a JSON string array.
            teachers_in_program = Teacher.query.join(Teacher.departments_assigned).filter(
                Department.name == program_code
            ).all()

            report_for_program = []
            for teacher in teachers_in_program:
                teacher_id_str = str(teacher.id)
                cnt = counts.get(teacher_id_str, 0)
                avg = (sums.get(teacher_id_str, 0.0) / cnt) if cnt > 0 else 0.0
                
                report_for_program.append({
                    'id': teacher.id,
                    'name': teacher.name,
                    'score': round(avg, 2),
                    'count': cnt
                })
            
            # Sort by score for ranking within the program
            report_for_program.sort(key=lambda x: x['score'], reverse=True)
            program_reports[program_code] = report_for_program
            
        return program_reports

    except Exception as e:
        logger.error(f"Critical error in calculate_program_reports: {e}")
        traceback.print_exc()
        return {p: [] for p in programs}

def calculate_detailed_scores_by_staff_type(staff_type='teaching'):
    """
    Calculates detailed scores for each staff member per criterion, total score, and rank,
    filtered by staff type ('teaching' or 'non_teaching').
    """
    try:
        # 1. Fetch all unique criteria
        all_questions = Question.query.order_by(Question.criteria).all()
        criteria_list = sorted(list({q.criteria for q in all_questions}))

        # 2. Filter teachers based on staff_type
        if staff_type == 'teaching':
            # Find teachers who are NOT in the 'Admin' department
            staff_query = Teacher.query.filter(
                ~Teacher.departments_assigned.any(Department.name == 'Admin')
            )
        else:  # non-teaching
            # Find teachers who ARE in the 'Admin' department
            staff_query = Teacher.query.join(Teacher.departments_assigned).filter(
                Department.name == 'Admin'
            )
        
        staff_list = staff_query.all()
        staff_map = {str(t.id): t for t in staff_list}
        staff_ids = set(staff_map.keys())

        if not staff_list:
            return [], []

        # 3. Fetch all relevant answers
        answers = db.session.query(Answer, Question).join(Question, Answer.question_identifier == Question.id).filter(Answer.response_value.like('%|%')).all()
        print(f"Found {len(answers)} answers for {staff_type} staff calculation")
        print(f"Staff IDs being checked: {list(staff_ids)[:3]}...")  # Show first 3 IDs

        # 4. Intermediate storage for scores
        scores_data = {}

        for ans, q in answers:
            try:
                # Handle both old format (score|teacher) and new format (score|teacher;score|teacher)
                teacher_scores = ans.response_value.split(';')
                
                for teacher_score in teacher_scores:
                    score_str, entity_id = teacher_score.split('|', 1)
                    logger.info(f"Processing answer: score={score_str}, teacher_id={entity_id}, criteria={q.criteria}")
                    
                    if entity_id in staff_ids:
                        score = float(score_str)
                        
                        if entity_id not in scores_data:
                            scores_data[entity_id] = {crit: {'sum': 0.0, 'count': 0} for crit in criteria_list}
                        
                        if q.criteria in scores_data[entity_id]:
                            scores_data[entity_id][q.criteria]['sum'] += score
                            scores_data[entity_id][q.criteria]['count'] += 1
                            logger.info(f"Added score {score} for teacher {entity_id}, criteria {q.criteria}")
                    else:
                        logger.info(f"Teacher ID {entity_id} not found in staff_ids")

            except (ValueError, IndexError) as e:
                logger.warning(f"Skipping malformed answer ID {ans.answer_id}: {ans.response_value}, Error: {e}")
                continue

        # 5. Process results - include all teachers with any evaluations
        results = []
        
        # Add teachers who have evaluation data
        for staff_id, criteria_scores in scores_data.items():
            staff_info = staff_map.get(staff_id)
            if not staff_info:
                continue

            total_score = 0
            avg_scores = {}
            for criterion in criteria_list:
                data = criteria_scores.get(criterion, {'sum': 0.0, 'count': 0})
                count = data['count']
                avg = (data['sum'] / count) if count > 0 else 0.0
                avg_scores[criterion] = avg
                total_score += avg

            result_item = {
                'StaffName': staff_info.name,
                'TotalScore': total_score,
                'Rank': 0
            }
            result_item.update(avg_scores)
            results.append(result_item)
        
        # Add teachers with no evaluations yet (show as 0.00)
        for staff_id, staff_info in staff_map.items():
            if staff_id not in scores_data:
                avg_scores = {criterion: 0.0 for criterion in criteria_list}
                result_item = {
                    'StaffName': staff_info.name,
                    'TotalScore': 0.0,
                    'Rank': 0
                }
                result_item.update(avg_scores)
                results.append(result_item)

        # 6. Sort by TotalScore to assign ranks
        results.sort(key=lambda x: x['TotalScore'], reverse=True)
        for i, res in enumerate(results):
            res['Rank'] = i + 1

        return results, criteria_list

    except Exception as e:
        logger.error(f"Critical error in calculate_detailed_scores_by_staff_type: {e}")
        traceback.print_exc()
        return [], []

@views.route('/admin')
@views.route('/admin/home')
@admin_required
def admin_home():
    """Route for the Staff/Admin Dashboard."""
    
    try:
        # Log access attempt for security monitoring
        logger.info(f"Admin dashboard access by user: {session.get('user_name', 'Unknown')}")
        
        # Define a safe fallback status object for the template in case of DB error
        SAFE_SURVEY_STATUS = type('SurveyStatusMock', (object,), {
            'is_active': False,
            'last_change': 'N/A'
        })()

        # Define a complete set of safe variables for the template
        SAFE_CONTEXT = {
            'questions': [], 
            'surveys': [],
            'survey_status': SAFE_SURVEY_STATUS,
            'teachers': [], 
            'non_teaching_staff': [], 
            'programs': [], 
            'mock_programs': ['BSCS', 'BSMA', 'BPA', 'BSCRIM'],
            # Results will be populated below
            'teaching_results': [],
            'teaching_criteria': [],
            'non_teaching_results': [],
            'non_teaching_criteria': [],
            'program_reports': {},
            'teacher_averages': [],
            'non_teaching_staff_averages': []
        }
        
        # --- Data Fetching ---
        try:
            # Check database connectivity (lightweight query)
            with db.engine.connect() as connection:
                connection.execute(text('SELECT 1'))
            logger.debug("Database connection successful for admin_home.")
            
            SAFE_CONTEXT['questions'] = Question.query.all()
            SAFE_CONTEXT['surveys'] = Survey.query.all()
            
            survey_status_db = SurveyStatus.query.get(1) 
            if survey_status_db:
                if survey_status_db.last_change is None:
                    survey_status_db.last_change = 'N/A'
                SAFE_CONTEXT['survey_status'] = survey_status_db
            
            # Add program monitoring data with CSV integration
            programs_monitoring = get_completion_stats_by_program()
            total_students = sum(p['students'] for p in programs_monitoring)
            total_completed = sum(p['completed'] for p in programs_monitoring)
            response_rate = int((total_completed / total_students) * 100) if total_students > 0 else 0
            
            SAFE_CONTEXT['programs'] = programs_monitoring
            SAFE_CONTEXT['response_rate'] = response_rate
            SAFE_CONTEXT['total_students'] = total_students
            SAFE_CONTEXT['dept_stats'] = programs_monitoring
            
            # Fetch all departments and sections for the teacher management forms
            SAFE_CONTEXT['all_departments'] = Department.query.all()
            SAFE_CONTEXT['all_sections'] = Section.query.all()

            # Fetch teachers with their assigned departments and sections eagerly loaded
            all_staff = Teacher.query.options(
                db.joinedload(Teacher.departments_assigned),
                db.joinedload(Teacher.sections_assigned)
            ).all()

            # Correctly filter staff based on the 'Admin' department in the many-to-many relationship
            SAFE_CONTEXT['teachers'] = [
                s for s in all_staff if 'Admin' not in {d.name for d in s.departments_assigned}
            ]
            SAFE_CONTEXT['non_teaching_staff'] = [
                s for s in all_staff if 'Admin' in {d.name for d in s.departments_assigned}
            ]

            SAFE_CONTEXT['teaching_results'], SAFE_CONTEXT['teaching_criteria'] = calculate_detailed_scores_by_staff_type('teaching')
            SAFE_CONTEXT['non_teaching_results'], SAFE_CONTEXT['non_teaching_criteria'] = calculate_detailed_scores_by_staff_type('non_teaching')

            # Restored logic for original course-based reports
            SAFE_CONTEXT['program_reports'] = calculate_program_reports(SAFE_CONTEXT['mock_programs'])

            # Add calls for original reports
            SAFE_CONTEXT['teacher_averages'] = calculate_teacher_averages()
            SAFE_CONTEXT['non_teaching_staff_averages'] = calculate_non_teaching_staff_averages()
            
            # Load current admin user info for settings page
            try:
                from .models import User
                current_user_id = session.get('user_id')
                if current_user_id:
                    current_user = User.query.get(uuid.UUID(current_user_id))
                    if current_user:
                        name_parts = current_user.name.split(' ', 1)
                        SAFE_CONTEXT['admin_info'] = {
                            'first_name': name_parts[0] if name_parts else 'Admin',
                            'last_name': name_parts[1] if len(name_parts) > 1 else 'User',
                            'email': current_user.email,
                            'full_name': current_user.name
                        }
                    else:
                        SAFE_CONTEXT['admin_info'] = {
                            'first_name': 'Admin',
                            'last_name': 'User', 
                            'email': 'admin@pgpc.edu',
                            'full_name': 'Admin User'
                        }
                else:
                    SAFE_CONTEXT['admin_info'] = {
                        'first_name': 'Admin',
                        'last_name': 'User',
                        'email': 'admin@pgpc.edu', 
                        'full_name': 'Admin User'
                    }
            except Exception as e:
                logger.error(f"Error loading admin info: {e}")
                SAFE_CONTEXT['admin_info'] = {
                    'first_name': 'Admin',
                    'last_name': 'User',
                    'email': 'admin@pgpc.edu',
                    'full_name': 'Admin User'
                }

            return render_template('admin.html', **SAFE_CONTEXT)
            
        except Exception as e:
            logger.error("CRITICAL Admin Home Error: %s", e)
            traceback.print_exc()
            flash(f'Application Data Error: {e}. Displaying limited data.', 'error')
            return render_template('admin.html', **SAFE_CONTEXT)
            
    except Exception as e:
        logger.error(f"Unexpected error in admin_home: {e}")
        traceback.print_exc()
        flash('An unexpected error occurred. Please try again or contact support.', 'error')
        return redirect(url_for('auth.login'))


@views.route('/survey/generate_results', methods=['POST'])
@admin_required
def generate_survey_results():
    """
    Recalculates all survey results from raw answers and stores them.
    """
    try:
        # Clear old results
        SurveyResult.query.delete()
        
        # Get all survey sessions
        sessions = SurveySession.query.all()
        results_created = 0
        
        for session in sessions:
            # Get answers for this session
            answers = Answer.query.filter_by(session_id=session.session_id).all()
            
            if not answers:
                continue
                
            # Calculate overall score for this session
            total_score = 0
            answer_count = 0
            category_scores = {}
            
            for answer in answers:
                # Parse the response value (format: "score|teacher_id" or "score|teacher_id;score|teacher_id")
                teacher_scores = answer.response_value.split(';')
                
                for teacher_score in teacher_scores:
                    try:
                        score_str, teacher_id = teacher_score.split('|', 1)
                        score = float(score_str)
                        total_score += score
                        answer_count += 1
                        
                        # Get question for category analysis
                        question = Question.query.get(answer.question_identifier)
                        if question and question.criteria:
                            if question.criteria not in category_scores:
                                category_scores[question.criteria] = {'sum': 0, 'count': 0}
                            category_scores[question.criteria]['sum'] += score
                            category_scores[question.criteria]['count'] += 1
                            
                    except (ValueError, IndexError):
                        continue
            
            # Calculate averages
            overall_score = (total_score / answer_count) if answer_count > 0 else 0
            
            # Prepare category analysis
            category_analysis = {}
            for category, data in category_scores.items():
                category_analysis[category] = data['sum'] / data['count'] if data['count'] > 0 else 0
            
            # Determine staff type based on survey
            staff_type = 'teaching'
            if session.survey_id:
                survey = Survey.query.get(session.survey_id)
                if survey:
                    staff_type = survey.staff_type
            
            # Create survey result
            result = SurveyResult(
                session_id=session.session_id,
                overall_score=round(overall_score, 2),
                staff_type=staff_type,
                category_analysis=category_analysis
            )
            
            db.session.add(result)
            results_created += 1
        
        db.session.commit()
        flash(f'Survey results generated successfully! Created {results_created} result records.', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'An error occurred while generating results: {e}', 'error')
        logger.error(f"Error in generate_survey_results: {e}")
        traceback.print_exc()

    return redirect(url_for('views.admin_home', _anchor='view-reports'))

@views.route('/report/generate_pdf')
@admin_required
def generate_results_pdf():
    """Generates a multi-page PDF report for all staff."""
    try:
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=landscape(letter))
        styles = getSampleStyleSheet()
        story = []

        for staff_type in ['teaching', 'non_teaching']:
            results, criteria = calculate_detailed_scores_by_staff_type(staff_type)
            
            if not results:
                story.append(Paragraph(f'No data available for {staff_type} staff.', styles['h2']))
                story.append(PageBreak())
                continue

            story.append(Paragraph(f'{staff_type.title()} Staff Evaluation Results', styles['h1']))
            story.append(Spacer(1, 12))

            headers = ['NO', 'Staff Name'] + criteria + ['TOTAL', 'RANK']
            table_data = [headers]

            for i, staff in enumerate(results):
                row = [i + 1, Paragraph(staff['StaffName'], styles['Normal'])]
                for crit in criteria:
                    row.append(f"{staff.get(crit, 0.0):.2f}")
                row.append(f"{staff['TotalScore']:.2f}")
                row.append(staff['Rank'])
                table_data.append(row)

            table = Table(table_data, repeatRows=1)
            style = TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ])
            table.setStyle(style)
            
            story.append(table)
            story.append(PageBreak())

        if not story:
            flash('No data available to generate a report.', 'warning')
            return redirect(url_for('views.admin_home', _anchor='view-reports'))

        doc.build(story)
        
        buffer.seek(0)
        return make_response(buffer.getvalue(), 200, {
            'Content-Type': 'application/pdf',
            'Content-Disposition': 'inline; filename="all_staff_results.pdf"'
        })

    except Exception as e:
        logger.error(f"Error generating combined PDF report: {e}")
        traceback.print_exc()
        flash('Could not generate PDF report due to an internal error.', 'error')
        return redirect(url_for('views.admin_home', _anchor='view-reports'))

@views.route('/ranking/post', methods=['POST'])
@admin_required
def post_rankings():
    """Publishes the rankings for teaching or non-teaching staff."""
    try:
        # Get actual teaching staff rankings
        teaching_rankings = calculate_teacher_averages()
        
        ranking_status = RankingStatus.query.first()
        if not ranking_status:
            ranking_status = RankingStatus(is_posted_teaching=True)
            db.session.add(ranking_status)
        else:
            ranking_status.is_posted_teaching = True
        
        # Format rankings for student display
        formatted_rankings = []
        for i, teacher in enumerate(teaching_rankings[:10]):  # Top 10
            formatted_rankings.append({
                'rank': i + 1,
                'name': teacher['name'],
                'department': teacher['department'],
                'score': teacher['score']
            })
        
        # Store in app config for global access
        current_app.config['PUBLISHED_RANKINGS'] = {
            'rankings': formatted_rankings,
            'published_date': datetime.utcnow().isoformat()
        }
        
        db.session.commit()
        
        flash('Teaching staff rankings posted successfully!', 'success')
        return jsonify({'status': 'success', 'message': 'Rankings posted.'})

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error in post_rankings: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@views.route('/generate_detailed_pdf_report/<staff_type>')
@admin_required
def generate_detailed_pdf_report(staff_type):
    """Generates a detailed PDF report for a given staff type."""
    try:
        results, criteria = calculate_detailed_scores_by_staff_type(staff_type)
        
        if not results:
            flash(f'No data available to generate a report for {staff_type} staff.', 'warning')
            return redirect(url_for('views.admin_home'))

        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        styles = getSampleStyleSheet()
        
        story = []
        story.append(Paragraph(f'{staff_type.title()} Staff Evaluation Results', styles['h1']))
        story.append(Spacer(1, 12))

        headers = ['NO', 'Staff Name'] + criteria + ['TOTAL', 'RANK']
        table_data = [headers]

        for i, staff in enumerate(results):
            row = [i + 1, Paragraph(staff['StaffName'], styles['Normal'])]
            for crit in criteria:
                row.append(f"{staff.get(crit, 0.0):.2f}")
            row.append(f"{staff['TotalScore']:.2f}")
            row.append(staff['Rank'])
            table_data.append(row)

        table = Table(table_data)
        style = TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ])
        table.setStyle(style)
        
        story.append(table)
        doc.build(story)
        
        buffer.seek(0)
        return make_response(buffer.getvalue(), 200, {
            'Content-Type': 'application/pdf',
            'Content-Disposition': f'inline; filename="{staff_type}_results.pdf"'
        })

    except Exception as e:
        logger.error(f"Error generating PDF for {staff_type}: {e}")
        flash('Could not generate PDF report.', 'error')
        return redirect(url_for('views.admin_home'))

@views.route('/generate_individual_staff_report/<uuid:teacher_id>')
@admin_required
def generate_individual_staff_report(teacher_id):
    """Generates a detailed PDF report for an individual staff member including comments."""
    try:
        teacher = Teacher.query.get(teacher_id)
        if not teacher:
            flash('Staff member not found.', 'error')
            return redirect(url_for('views.admin_home'))

        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        styles = getSampleStyleSheet()
        
        story = []
        story.append(Paragraph(f'Individual Staff Report: {teacher.name}', styles['h1']))
        story.append(Spacer(1, 12))
        
        # Calculate individual scores
        sums = {}
        counts = {}
        answers = Answer.query.filter(Answer.response_value.like('%|%')).all()
        
        for ans in answers:
            try:
                teacher_scores = ans.response_value.split(';')
                for teacher_score in teacher_scores:
                    score_str, entity_id = teacher_score.split('|', 1)
                    if entity_id == str(teacher_id):
                        score = float(score_str)
                        question = Question.query.get(ans.question_identifier)
                        if question:
                            criteria = question.criteria
                            if criteria not in sums:
                                sums[criteria] = 0.0
                                counts[criteria] = 0
                            sums[criteria] += score
                            counts[criteria] += 1
            except (ValueError, IndexError):
                continue
        
        # Overall score calculation
        total_score = sum(sums[crit] / counts[crit] for crit in sums if counts[crit] > 0)
        avg_score = total_score / len(sums) if sums else 0.0
        
        # Staff information
        story.append(Paragraph(f'Staff Name: {teacher.name}', styles['h2']))
        story.append(Paragraph(f'Overall Score: {avg_score:.2f}/5.00', styles['h2']))
        story.append(Spacer(1, 12))
        
        # Detailed scores by criteria
        if sums:
            story.append(Paragraph('Evaluation Scores by Criteria:', styles['h3']))
            criteria_data = [['Criteria', 'Average Score', 'Total Responses']]
            
            for criteria in sorted(sums.keys()):
                avg = sums[criteria] / counts[criteria] if counts[criteria] > 0 else 0.0
                criteria_data.append([criteria, f'{avg:.2f}', str(counts[criteria])])
            
            criteria_table = Table(criteria_data)
            criteria_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            story.append(criteria_table)
            story.append(Spacer(1, 20))
        
        # Comments section
        comments = StudentComment.query.filter_by(teacher_id=teacher_id).all()
        
        if comments:
            story.append(Paragraph('Student Comments and Suggestions:', styles['h3']))
            story.append(Spacer(1, 12))
            
            for i, comment in enumerate(comments, 1):
                story.append(Paragraph(f'Comment {i}:', styles['h4']))
                story.append(Paragraph(comment.comment_text, styles['Normal']))
                story.append(Paragraph(f'Submitted: {comment.created_at.strftime("%B %d, %Y")}', styles['Italic']))
                story.append(Spacer(1, 12))
        else:
            story.append(Paragraph('Student Comments and Suggestions:', styles['h3']))
            story.append(Paragraph('No comments were submitted for this staff member.', styles['Normal']))
        
        doc.build(story)
        
        buffer.seek(0)
        return make_response(buffer.getvalue(), 200, {
            'Content-Type': 'application/pdf',
            'Content-Disposition': f'inline; filename="{teacher.name.replace(" ", "_")}_individual_report.pdf"'
        })

    except Exception as e:
        logger.error(f"Error generating individual report for teacher {teacher_id}: {e}")
        traceback.print_exc()
        flash('Could not generate individual staff report.', 'error')
        return redirect(url_for('views.admin_home'))

# --- EMAIL REMINDER LOGIC ---
def load_students_from_csv():
    """Load students from CSV file."""
    import csv
    csv_path = os.path.join(os.path.dirname(__file__), 'data', 'students_data.csv')
    students = []
    
    try:
        with open(csv_path, 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            for row in reader:
                students.append({
                    'full_name': row['full_name'].strip(),
                    'email': row['email'].strip(),
                    'student_id': row['student_id'].strip(),
                    'program': row['program'].strip(),
                    'section': row['section'].strip()
                })
        return students
    except Exception as e:
        logger.error(f"Error loading CSV: {e}")
        return []

def sync_csv_to_database():
    """Sync CSV student data to database for login functionality."""
    from werkzeug.security import generate_password_hash
    
    try:
        csv_students = load_students_from_csv()
        if not csv_students:
            return 0, 0
        
        added_count = 0
        updated_count = 0
        
        for student_data in csv_students:
            # Check if student already exists
            existing_student = Student.query.filter_by(student_id=student_data['student_id']).first()
            
            if not existing_student:
                # Create new student with default password (student_id)
                new_student = Student(
                    full_name=student_data['full_name'],
                    email=student_data['email'],
                    student_id=student_data['student_id'],
                    program=student_data['program'],
                    section=student_data['section'],
                    password_hash=generate_password_hash(student_data['student_id'], method='pbkdf2:sha256'),
                    password_changed=False  # Force password change on first login
                )
                db.session.add(new_student)
                added_count += 1
            else:
                # Update existing student info (except password)
                existing_student.full_name = student_data['full_name']
                existing_student.email = student_data['email']
                existing_student.program = student_data['program']
                existing_student.section = student_data['section']
                updated_count += 1
        
        db.session.commit()
        return added_count, updated_count
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error syncing CSV to database: {e}")
        return 0, 0

def get_completion_stats_by_program():
    """Calculate real completion percentages based on CSV data."""
    csv_students = load_students_from_csv()
    if not csv_students:
        return []
    
    # Get completed student IDs
    completed_student_ids = set()
    completed_sessions = SurveySession.query.all()
    for session in completed_sessions:
        student = Student.query.get(session.student_uuid)
        if student:
            completed_student_ids.add(student.student_id)
    
    # Group by program
    program_stats = {}
    for student in csv_students:
        program = student['program']
        if program not in program_stats:
            program_stats[program] = {'total': 0, 'completed': 0, 'students': []}
        
        program_stats[program]['total'] += 1
        program_stats[program]['students'].append(student)
        
        if student['student_id'] in completed_student_ids:
            program_stats[program]['completed'] += 1
    
    # Format results
    result = []
    for program, stats in program_stats.items():
        pending = stats['total'] - stats['completed']
        rate = int((stats['completed'] / stats['total']) * 100) if stats['total'] > 0 else 0
        result.append({
            'name': program,
            'students': stats['total'],
            'completed': stats['completed'],
            'pending': pending,
            'completion_rate': f"{rate}%",
            'rate': rate,
            'responses': stats['completed']
        })
    
    return result

@views.route('/send-reminders', methods=['POST'])
@admin_required
def send_reminders():
    """Send reminders using CSV data and email service."""
    data = request.get_json(silent=True) or {}
    target_program = data.get('program_name')
    
    try:
        csv_students = load_students_from_csv()
        if not csv_students:
            return jsonify({'status': 'error', 'message': 'Could not load student data'}), 500
        
        # Get completed student IDs
        completed_student_ids = set()
        completed_sessions = SurveySession.query.all()
        for session in completed_sessions:
            student = Student.query.get(session.student_uuid)
            if student:
                completed_student_ids.add(student.student_id)
        
        # Filter students to remind
        students_to_remind = []
        for student in csv_students:
            if target_program and student['program'] != target_program:
                continue
            if student['student_id'] not in completed_student_ids:
                students_to_remind.append(student)
        
        if not students_to_remind:
            program_msg = f" in {target_program}" if target_program else ""
            return jsonify({'status': 'info', 'message': f'All students{program_msg} have completed their evaluations.'})
        
        # Send emails
        from .email_service import send_reminder_email
        sent_count = 0
        failed_count = 0
        
        for student in students_to_remind:
            try:
                success = send_reminder_email(
                    student['email'], student['full_name'], 
                    student['program'], student['section']
                )
                if success:
                    sent_count += 1
                else:
                    failed_count += 1
            except Exception as e:
                failed_count += 1
                logger.error(f"Error sending to {student['full_name']}: {e}")
        
        program_suffix = f" in {target_program}" if target_program else ""
        
        if sent_count > 0:
            message = f'✅ Sent {sent_count} email reminders{program_suffix}.'
            status = 'success'
        else:
            message = f'⚠️ {failed_count} emails failed to send.'
            status = 'warning'
        
        return jsonify({
            'status': status,
            'message': message,
            'sent_count': sent_count,
            'failed_count': failed_count
        })
        
    except Exception as e:
        logger.error(f"Error in send_reminders: {e}")
        return jsonify({'status': 'error', 'message': 'Error sending reminders'}), 500

@views.route('/api/completion-stats')
@admin_required
def get_completion_stats():
    """API endpoint for completion statistics."""
    try:
        stats = get_completion_stats_by_program()
        return jsonify(stats)
    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        return jsonify([])

@views.route('/email/send_reminder', methods=['POST'])
@admin_required
def send_reminder():
    """Legacy route - redirects to new implementation."""
    return send_reminders()

@views.route('/sync-csv-students', methods=['POST'])
@admin_required
def sync_csv_students():
    """Sync CSV student data to database for login functionality."""
    try:
        added_count, updated_count = sync_csv_to_database()
        
        if added_count > 0 or updated_count > 0:
            message = f'✅ Sync completed: {added_count} students added, {updated_count} students updated.'
            status = 'success'
        else:
            message = 'ℹ️ No changes needed. All CSV data is already synced.'
            status = 'info'
        
        return jsonify({
            'status': status,
            'message': message,
            'added_count': added_count,
            'updated_count': updated_count
        })
        
    except Exception as e:
        logger.error(f"Error in sync_csv_students: {e}")
        return jsonify({'status': 'error', 'message': 'Error syncing student data'}), 500




@views.route('/ranking/save_draft', methods=['POST'])
@admin_required
def save_ranking_draft():
    try:
        data = request.get_json()
        session['ranking_draft'] = {
            'rankings': data.get('rankings', []),
            'timestamp': datetime.utcnow().isoformat(),
            'status': 'draft'
        }
        return jsonify({'status': 'success', 'message': 'Draft saved successfully'}), 200
    except Exception as e:
        logger.error('Error saving ranking draft: %s', e)
        return jsonify({'status': 'error', 'message': str(e)}), 400

@views.route('/ranking/get_draft', methods=['GET'])
@admin_required
def get_ranking_draft():
    try:
        draft = session.get('ranking_draft', {})
        return jsonify(draft), 200
    except Exception as e:
        logger.error('Error getting ranking draft: %s', e)
        return jsonify({'status': 'error', 'message': str(e)}), 400

@views.route('/ranking/post_final', methods=['POST'])
@admin_required
def post_final_ranking():
    try:
        # Get actual teaching staff rankings
        teaching_rankings = calculate_teacher_averages()
        
        ranking_status = RankingStatus.query.first()
        if not ranking_status:
            ranking_status = RankingStatus(is_posted_teaching=True)
            db.session.add(ranking_status)
        else:
            ranking_status.is_posted_teaching = True
        
        # Format rankings for student display
        formatted_rankings = []
        for i, teacher in enumerate(teaching_rankings[:10]):  # Top 10
            formatted_rankings.append({
                'rank': i + 1,
                'name': teacher['name'],
                'department': teacher['department'],
                'score': teacher['score']
            })
        
        # Store rankings in database for all users to access
        from flask import current_app
        import json
        
        rankings_data = {
            'rankings': formatted_rankings,
            'published_date': datetime.utcnow().isoformat()
        }
        
        # Store in app config for global access
        current_app.config['PUBLISHED_RANKINGS'] = rankings_data
        
        db.session.commit()
        flash('Final rankings have been successfully posted and are now visible to students.', 'success')
        return jsonify({'status': 'success', 'message': 'Final rankings posted'}), 200
    except Exception as e:
        db.session.rollback()
        logger.error('Error posting final ranking: %s', e)
        return jsonify({'status': 'error', 'message': str(e)}), 400





@views.route('/survey/activate', methods=['POST'])
@admin_required
def activate_survey_default():
    logger.debug("Received request to activate a default survey.")
    try:
        # Find the first inactive survey to activate
        survey_to_activate = Survey.query.filter_by(is_active=False).first()
        if not survey_to_activate:
            logger.warning("No inactive surveys found to activate for default route.")
            return jsonify({'status': 'error', 'message': 'No inactive surveys found to activate'}), 400
        
        logger.debug(f"Calling activate_survey_by_id with ID: {survey_to_activate.id}")
        # Call the original function with the found survey's ID
        return activate_survey_by_id(str(survey_to_activate.id))
    except Exception as e:
        logger.error(f'Error in activate_survey_default: {e}')
        traceback.print_exc()
        return jsonify({'status': 'error', 'message': str(e)}), 500

# FIX: The URL path must match the client-side request /survey/activate/<ID>
@views.route('/survey/activate/<survey_id>', methods=['POST'])
@admin_required
def activate_survey_by_id(survey_id):
    logger.debug(f"Attempting to activate survey with ID: {survey_id}")
    try:
        try:
            survey_uuid = uuid.UUID(survey_id)
        except ValueError:
            logger.error(f"Invalid UUID format for survey_id: {survey_id}")
            return jsonify({'status': 'error', 'message': 'Invalid survey ID format'}), 400
            
        survey_to_activate = Survey.query.get(survey_uuid)

        if not survey_to_activate:
            logger.warning(f"Survey with ID {survey_id} not found for activation.")
            return jsonify({'success': False, 'message': 'Survey not found.'}), 404

        logger.debug(f"Found survey to activate: {survey_to_activate.title} (Staff Type: {survey_to_activate.staff_type})")

        # Get current active surveys of the same type (excluding the one to activate)
        surveys_to_deactivate = Survey.query.filter(
            Survey.staff_type == survey_to_activate.staff_type,
            Survey.id != survey_to_activate.id,
            Survey.is_active == True
        ).all()

        affected_surveys_list = []
        for s in surveys_to_deactivate:
            s.is_active = False
            affected_surveys_list.append({'id': str(s.id), 'is_active': False})
            logger.debug(f"Deactivated existing active survey: {s.title}")

        survey_to_activate.is_active = True
        affected_surveys_list.append({'id': str(survey_to_activate.id), 'is_active': True})
        logger.debug(f"Activated survey: {survey_to_activate.title}")

        # Update global SurveyStatus
        survey_status = SurveyStatus.query.get(1)
        if not survey_status:
            survey_status = SurveyStatus(id=1, is_active=True, last_change=datetime.utcnow())
            db.session.add(survey_status)
            logger.debug("Created new global SurveyStatus record.")
        else:
            survey_status.is_active = True
            survey_status.last_change = datetime.utcnow()
            logger.debug("Updated global SurveyStatus to active.")

        db.session.commit()
        logger.debug("Database commit successful for survey activation.")

        global_active_status = SurveyStatus.query.get(1).is_active if SurveyStatus.query.get(1) else False
        logger.debug(f"Final global active status after commit: {global_active_status}")

        return jsonify({
            'status': 'success', # Changed from 'success': True
            'new_status': 'active',
            'message': 'Survey activated successfully.',
            'survey_id': str(survey_to_activate.id),
            'is_active': True,
            'staff_type': survey_to_activate.staff_type,
            'global_survey_active': global_active_status,
            'affected_surveys': affected_surveys_list
        }), 200
    except Exception as e:
        db.session.rollback()
        logger.error(f'Error activating survey {survey_id}: {e}')
        traceback.print_exc()
        return jsonify({'status': 'error', 'message': str(e)}), 500



@views.route('/survey/deactivate', methods=['POST'])
@admin_required
def deactivate_survey_default():
    logger.debug("Received request to deactivate a default survey.")
    try:
        # Find the first active survey to deactivate
        survey_to_deactivate = Survey.query.filter_by(is_active=True).first()
        if not survey_to_deactivate:
            logger.warning("No active surveys found to deactivate for default route.")
            return jsonify({'status': 'error', 'message': 'No active surveys found to deactivate'}), 400
        
        logger.debug(f"Calling deactivate_survey_by_id with ID: {survey_to_deactivate.id}")
        # Call the original function with the found survey's ID
        return deactivate_survey_by_id(str(survey_to_deactivate.id))
    except Exception as e:
        logger.error(f'Error in deactivate_survey_default: {e}')
        traceback.print_exc()
        return jsonify({'status': 'error', 'message': str(e)}), 500


@views.route('/survey/deactivate/<survey_id>', methods=['POST'])
@admin_required
def deactivate_survey_by_id(survey_id):
    logger.debug(f"Attempting to deactivate survey with ID: {survey_id}")
    try:
        try:
            survey_uuid = uuid.UUID(survey_id)
        except ValueError:
            logger.error(f"Invalid UUID format for survey_id: {survey_id}")
            return jsonify({'status': 'error', 'message': 'Invalid survey ID format'}), 400
            
        survey_to_deactivate = Survey.query.get(survey_uuid)
        if not survey_to_deactivate:
            logger.warning(f"Survey with ID {survey_id} not found for deactivation.")
            return jsonify({'success': False, 'message': 'Survey not found.'}), 404

        logger.debug(f"Found survey to deactivate: {survey_to_deactivate.title}")

        affected_surveys_list = []
        survey_to_deactivate.is_active = False
        affected_surveys_list.append({'id': str(survey_to_deactivate.id), 'is_active': False})
        logger.debug(f"Deactivated survey: {survey_to_deactivate.title}")

        # UPDATE GLOBAL SURVEY STATUS
        survey_status = SurveyStatus.query.get(1)
        if survey_status:
            # If after deactivating, no other survey is active → global inactive
            if not Survey.query.filter_by(is_active=True).first():
                survey_status.is_active = False
                survey_status.last_change = datetime.utcnow()
                logger.debug("Updated global SurveyStatus to inactive.")
            else:
                logger.debug("Other surveys still active → global SurveyStatus stays active.")
        else:
            # Create if missing
            survey_status = SurveyStatus(id=1, is_active=False, last_change=datetime.utcnow())
            db.session.add(survey_status)
            logger.debug("Created new global SurveyStatus record (inactive).")

        db.session.commit()
        logger.debug("Database commit successful for survey deactivation.")

        global_active_status = SurveyStatus.query.get(1).is_active if SurveyStatus.query.get(1) else False
        logger.debug(f"Final global active status after commit: {global_active_status}")

        return jsonify({
            'status': 'success',
            'new_status': 'inactive',
            'message': 'Survey deactivated successfully.',
            'survey_id': str(survey_to_deactivate.id),
            'is_active': False,
            'staff_type': survey_to_deactivate.staff_type,
            'global_survey_active': global_active_status,
            'affected_surveys': affected_surveys_list
        }), 200

    except Exception as e:
        db.session.rollback()
        logger.error(f'Error deactivating survey {survey_id}: {e}')
        traceback.print_exc()
        return jsonify({'status': 'error', 'message': str(e)}), 500




@views.route('/ranking/edit_score', methods=['POST'])

@admin_required
def edit_score():
    data = request.get_json()
    staff_id = data.get('staff_id')
    new_score = data.get('new_score')

    try:
        return jsonify({'status': 'success', 'message': 'Score updated in interface'}), 200
    except Exception as e:
        logger.error('Error in edit score placeholder: %s', e)
        return jsonify({'status': 'error', 'message': str(e)}), 400

@views.route('/uploads/<path:filename>')
@login_required
def serve_uploaded_file(filename):
    """ 🔐 NEW: Securely serve files from a protected directory. """
    # Use instance_path, which is designed for non-public files.
    upload_dir = os.path.join(current_app.instance_path, 'uploads')
    return send_from_directory(upload_dir, filename)

def save_uploaded_file(file, prefix='teacher'):
    if file and file.filename:
        filename = f"{prefix}_{uuid.uuid4().hex[:8]}_{file.filename}"
        # 🔐 MODIFIED: Save to a non-public directory within the instance folder
        upload_dir = os.path.join(current_app.instance_path, 'uploads')
        os.makedirs(upload_dir, exist_ok=True)
        file_path = os.path.join(upload_dir, filename)
        file.save(file_path)
        # 🔐 MODIFIED: Return a URL to the protected route, not a direct file path
        return url_for('views.serve_uploaded_file', filename=filename)
    return None

@views.route('/save_teacher_profile', methods=['POST'])
@admin_required
def save_teacher_profile():
    teacher_id_str = request.form.get('teacher_id')
    staff_type = request.form.get('staff_type', 'teaching')
    
    name = request.form.get('name') or request.form.get('non_teaching_name')
    email = request.form.get('email')
    # Set email to None if empty to avoid unique constraint violation
    if not email or not email.strip():
        email = None

    # Get department and section names from form (new format: DEPARTMENT-SECTION)
    department_names = request.form.getlist('departments')
    section_values = request.form.getlist('sections')
    
    # Validation for teaching staff
    if staff_type == 'teaching':
        if not department_names:
            flash('Teaching staff must have at least one department selected.', 'error')
            return redirect(url_for('views.admin_home') + '#view-teachers')
        if not section_values:
            flash('Teaching staff must have at least one section selected.', 'error')
            return redirect(url_for('views.admin_home') + '#view-teachers')
    
    # Handle profile image upload
    image_url = None
    if 'image_file' in request.files and request.files['image_file'].filename:
        file = request.files['image_file']
        image_url = save_uploaded_file(file, 'teacher')
    
    if not image_url and teacher_id_str == 'new':
        image_url = f"https://placehold.co/100x100/5070ff/ffffff?text={name[:2].upper()}"

    try:
        if teacher_id_str == 'new':
            # Check for existing teacher by name or email (only check email if it's not empty)
            existing_by_name = Teacher.query.filter_by(name=name).first()
            existing_by_email = Teacher.query.filter_by(email=email).first() if email and email.strip() else None
            
            if existing_by_name or existing_by_email:
                flash(f'A staff member with the name "{name}" or email "{email}" already exists.', 'warning')
                return redirect(url_for('views.admin_home') + '#view-teachers')

            # Create new teacher
            teacher = Teacher(
                name=name, 
                email=email,
                image_url=image_url,
                department=department_names[0] if department_names else None,
                section=section_values[0].split('-')[1] if section_values else None
            )
            db.session.add(teacher)
            db.session.flush()

            # Handle many-to-many relationships for new teacher
            if staff_type == 'teaching':
                # Create/find departments and sections
                for dept_name in department_names:
                    department = Department.query.filter_by(name=dept_name).first()
                    if not department:
                        department = Department(name=dept_name)
                        db.session.add(department)
                        db.session.flush()
                    if department not in teacher.departments_assigned:
                        teacher.departments_assigned.append(department)
                
                for section_value in section_values:
                    dept_name, sec_name = section_value.split('-', 1)
                    department = Department.query.filter_by(name=dept_name).first()
                    if department:
                        section = Section.query.filter_by(name=sec_name, department_id=department.id).first()
                        if not section:
                            section = Section(name=sec_name, department_id=department.id)
                            db.session.add(section)
                            db.session.flush()
                        if section not in teacher.sections_assigned:
                            teacher.sections_assigned.append(section)
            else:
                # For non-teaching staff
                admin_dep = Department.query.filter_by(name='Admin').first()
                if not admin_dep:
                    admin_dep = Department(name='Admin')
                    db.session.add(admin_dep)
                    db.session.flush()
                if admin_dep not in teacher.departments_assigned:
                    teacher.departments_assigned.append(admin_dep)
                
                admin_sec = Section.query.filter_by(name='Admin-Office', department_id=admin_dep.id).first()
                if not admin_sec:
                    admin_sec = Section(name='Admin-Office', department_id=admin_dep.id)
                    db.session.add(admin_sec)
                    db.session.flush()
                if admin_sec not in teacher.sections_assigned:
                    teacher.sections_assigned.append(admin_sec)
                
            flash('Staff profile added successfully.', 'success')
        else:
            teacher_id_uuid = uuid.UUID(teacher_id_str)
            teacher = Teacher.query.get(teacher_id_uuid)
            
            if teacher:
                # Check for existing teacher by name or email, excluding self (only check email if it's not empty)
                existing_by_name = Teacher.query.filter(Teacher.name == name, Teacher.id != teacher_id_uuid).first()
                existing_by_email = Teacher.query.filter(Teacher.email == email, Teacher.id != teacher_id_uuid).first() if email and email.strip() else None
                
                if existing_by_name or existing_by_email:
                    flash(f'A different staff member with the name "{name}" or email "{email}" already exists.', 'warning')
                    return redirect(url_for('views.admin_home') + '#view-teachers')

                teacher.name = name
                teacher.email = email
                teacher.department = department_names[0] if department_names else None
                teacher.section = section_values[0].split('-')[1] if section_values else None
                
                # Update image_url only if a new file is uploaded
                if 'image_file' in request.files and request.files['image_file'].filename:
                    teacher.image_url = image_url
                elif teacher.image_url is None:
                    teacher.image_url = f"https://placehold.co/100x100/5070ff/ffffff?text={name[:2].upper()}"

                # Clear existing many-to-many relationships
                teacher.departments_assigned.clear()
                teacher.sections_assigned.clear()

                # Add new many-to-many relationships
                if staff_type == 'teaching':
                    for dept_name in department_names:
                        department = Department.query.filter_by(name=dept_name).first()
                        if not department:
                            department = Department(name=dept_name)
                            db.session.add(department)
                            db.session.flush()
                        if department not in teacher.departments_assigned:
                            teacher.departments_assigned.append(department)
                    
                    for section_value in section_values:
                        dept_name, sec_name = section_value.split('-', 1)
                        department = Department.query.filter_by(name=dept_name).first()
                        if department:
                            section = Section.query.filter_by(name=sec_name, department_id=department.id).first()
                            if not section:
                                section = Section(name=sec_name, department_id=department.id)
                                db.session.add(section)
                                db.session.flush()
                            if section not in teacher.sections_assigned:
                                teacher.sections_assigned.append(section)
                else:
                    # For non-teaching staff
                    admin_dep = Department.query.filter_by(name='Admin').first()
                    if not admin_dep:
                        admin_dep = Department(name='Admin')
                        db.session.add(admin_dep)
                        db.session.flush()
                    if admin_dep not in teacher.departments_assigned:
                        teacher.departments_assigned.append(admin_dep)
                    
                    admin_sec = Section.query.filter_by(name='Admin-Office', department_id=admin_dep.id).first()
                    if not admin_sec:
                        admin_sec = Section(name='Admin-Office', department_id=admin_dep.id)
                        db.session.add(admin_sec)
                        db.session.flush()
                    if admin_sec not in teacher.sections_assigned:
                        teacher.sections_assigned.append(admin_sec)

                flash('Staff profile updated successfully.', 'success')
            else:
                flash('Staff not found.', 'error')
        
        db.session.commit()
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error saving staff profile: {e}', 'error')
        traceback.print_exc()

    return redirect(url_for('views.admin_home') + '#view-teachers')

@views.route('/delete_teacher_profile/<teacher_id_str>', methods=['POST'])
@admin_required
def delete_teacher_profile(teacher_id_str):
    try:
        teacher_id_uuid = uuid.UUID(teacher_id_str) 
        teacher = Teacher.query.get(teacher_id_uuid)
        if teacher:
            db.session.delete(teacher)
            db.session.commit()
            flash('Teacher profile deleted successfully.', 'success')
        else:
            flash('Teacher not found.', 'error')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting teacher profile: {e}', 'error')
        traceback.print_exc()

    return redirect(url_for('views.admin_home') + '#view-teachers')

@views.route('/survey/create', methods=['POST'])
@admin_required
def create_survey():
    title = request.form.get('title')
    description = request.form.get('description')
    semester = request.form.get('semester')
    staff_type = request.form.get('staff_type')
    
    try:
        new_survey = Survey(
            title=title,
            description=description,
            semester=semester,
            staff_type=staff_type,
            is_active=False
        )
        db.session.add(new_survey)
        db.session.commit()
        flash(f'Survey "{title}" created successfully.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error creating survey: {e}', 'error')
        logger.error(f"Error creating survey: {e}")

    return redirect(url_for('views.admin_home', _anchor='view-survey'))

@views.route('/delete_survey/<survey_identifier>', methods=['POST'])
@admin_required
def delete_survey(survey_identifier):
    try:
        try:
            survey_uuid = uuid.UUID(survey_identifier)
            survey = Survey.query.get(survey_uuid)
        except ValueError:
            flash('Invalid survey ID format.', 'error')
            return redirect(url_for('views.admin_home') + '#view-survey')
        
        if survey:
            Question.query.filter_by(survey_id=survey_uuid).delete()
            db.session.delete(survey)
            db.session.commit()
            flash(f'Survey "{survey.title}" and all its questions deleted successfully.', 'success')
        else:
            flash('Survey not found.', 'error')
            return redirect(url_for('views.admin_home') + '#view-survey')
    
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting survey: {e}', 'error')
        traceback.print_exc()

    return redirect(url_for('views.admin_home') + '#view-survey')

@views.route('/add_question', methods=['POST'])
@admin_required
def add_question():
    criteria = request.form.get('criteria')
    question_text = request.form.get('question_text')
    staff_type = request.form.get('staff_type')

    try:
        # Find or create a survey for the specified staff type
        survey = Survey.query.filter_by(staff_type=staff_type).first()
        if not survey:
            # Create a default survey for this staff type
            survey_title = f"{staff_type.replace('_', ' ').title()} Staff Evaluation"
            survey = Survey(
                title=survey_title,
                description=f"Default survey for {staff_type.replace('_', ' ')} staff evaluation",
                staff_type=staff_type,
                is_active=False
            )
            db.session.add(survey)
            db.session.flush()
            
        question = Question(
            criteria=criteria, 
            text=question_text, 
            survey_id=survey.id
        )
        db.session.add(question)
        db.session.commit()
        flash('Question added successfully!', 'success')
            
    except Exception as e:
        db.session.rollback()
        flash(f'Error adding question: {e}', 'error')
        logger.error("Error adding question: %s", e)
    
    return redirect(url_for('views.manage_questions'))

@views.route('/delete_question/<question_id_str>', methods=['POST'])
@admin_required
def delete_question(question_id_str):
    """ 🔐 NEW: Route to handle question deletion. """
    try:
        # Convert string ID to UUID for database query
        question_id_uuid = uuid.UUID(question_id_str)
        question = Question.query.get(question_id_uuid)
        
        if question:
            db.session.delete(question)
            db.session.commit()
            flash('Question deleted successfully.', 'success')
        else:
            flash('Question not found.', 'error')
            
    except ValueError:
        flash('Invalid question ID format.', 'error')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting question: {e}', 'error')
        logger.error("Error deleting question: %s", e)
        traceback.print_exc()

    # Redirect back to the manage questions page
    return redirect(url_for('views.manage_questions'))

@views.route('/edit_question/<question_id_str>', methods=['POST'])
@admin_required
def edit_question(question_id_str):
    try:
        question_id_uuid = uuid.UUID(question_id_str)
        question = Question.query.get(question_id_uuid)

        if not question:
            flash('Question not found.', 'error')
            return redirect(url_for('views.manage_questions'))

        criteria = request.form.get('criteria')
        question_text = request.form.get('question_text')
        staff_type = request.form.get('staff_type')

        question.criteria = criteria
        question.text = question_text
        
        # Find or create a survey for the specified staff type
        if staff_type:
            survey = Survey.query.filter_by(staff_type=staff_type).first()
            if not survey:
                # Create a default survey for this staff type
                survey_title = f"{staff_type.replace('_', ' ').title()} Staff Evaluation"
                survey = Survey(
                    title=survey_title,
                    description=f"Default survey for {staff_type.replace('_', ' ')} staff evaluation",
                    staff_type=staff_type,
                    is_active=False
                )
                db.session.add(survey)
                db.session.flush()
            question.survey_id = survey.id
        else:
            question.survey_id = None

        db.session.commit()
        flash('Question updated successfully!', 'success')

    except ValueError:
        flash('Invalid question ID format.', 'error')
    except Exception as e:
        db.session.rollback()
        flash(f'Error updating question: {e}', 'error')
        logger.error("Error updating question: %s", e)
        traceback.print_exc()
    
    return redirect(url_for('views.manage_questions'))

@views.route('/dashboard/submission-stats')
@admin_required
def submission_stats():
    """
    Provides data for the survey completion charts on the admin dashboard.
    """
    try:
        # Get total number of students
        total_students = db.session.query(func.count(Student.id)).scalar()
        
        # Get the number of unique students who have a record in SurveySession
        completed_students = db.session.query(func.count(func.distinct(SurveySession.student_uuid))).scalar()
        
        pending_students = total_students - completed_students
        
        # The chart logic is built to handle data per program, so we will return an aggregated "Overall" stat
        stats = [
            {
                "program": "Overall",
                "completed": completed_students,
                "pending": pending_students
            }
        ]
        
        return jsonify(stats)

    except Exception as e:
        logger.error(f"Error in submission_stats: {e}")
        traceback.print_exc()
        return jsonify([]), 500


@views.route('/get_survey_questions/<survey_identifier>')
@admin_required
def get_survey_questions(survey_identifier):
    questions_data = []
    
    try:
        survey_uuid = uuid.UUID(survey_identifier)
        questions = Question.query.filter_by(survey_id=survey_uuid).all()
        
        for question in questions:
            questions_data.append({
                'id': str(question.id),
                'criteria': question.criteria,
                'text': question.text
            })
        
        return jsonify(questions_data)
        
    except ValueError:
        if survey_identifier in ['teaching_survey', 'non_teaching_survey']:
            questions = Question.query.filter_by(survey_type=survey_identifier).all()
            for question in questions:
                questions_data.append({
                    'id': str(question.id),
                    'criteria': question.criteria,
                    'text': question.text
                })
            return jsonify(questions_data)
            
        return jsonify([]), 400

    except Exception as e:
        logger.error("Error getting survey questions: %s", e)
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@views.route('/manage-questions')
@admin_required
def manage_questions():
    try:
        all_questions = Question.query.all()
        all_surveys = Survey.query.all()
        return render_template('manage_questions.html', questions=all_questions, surveys=all_surveys)
    except Exception as e:
        logger.error("Error loading manage questions page: %s", e)
        flash('Could not load questions management page.', 'error')
        return redirect(url_for('views.admin_home'))

@views.route('/teacher/add', methods=['POST'])
@admin_required
def add_teacher():
    """Route to add a new teacher."""
    # This route now acts as a wrapper for save_teacher_profile
    # The form should submit here, and then this function will call the core logic
    return save_teacher_profile()

@views.route('/teacher/edit/<teacher_id>', methods=['POST'])
@admin_required
def edit_teacher(teacher_id):
    """Route to edit an existing teacher."""
    # This also wraps save_teacher_profile, ensuring the teacher_id from the URL
    # is available if needed, although the form is expected to contain it.
    return save_teacher_profile()

@views.route('/teacher/delete/<teacher_id>', methods=['POST'])
@admin_required
def delete_teacher(teacher_id):
    """Route to delete a teacher."""
    # A wrapper for the delete_teacher_profile function
    return delete_teacher_profile(teacher_id)

@views.route('/student')
@views.route('/student/home')
@login_required
def student_home():
    """Route for the Student Dashboard."""
    if session.get('user_role') != 'student':
        flash('Student access required.', 'error')
        return redirect(url_for('auth.login'))
    
    student_id_str = session.get('user_id')
    
    # Define safe defaults for the template context
    safe_context = {
        'profile': {'name': session.get('user_name', 'Student'), 'program': 'N/A', 'section': 'N/A', 'email': 'N/A'},
        'survey_active': False,
        'evaluation_complete': False,
        'my_teachers': [],
        'questions': [],
        'published_rankings': [],
        'can_submit': False,
        'review_mode': False,
        'show_form': False,
        'survey_closed_message': None
    }

    try:
        # Get current student
        current_student = None
        if student_id_str:
            try:
                current_student = Student.query.get(uuid.UUID(student_id_str))
            except ValueError:
                logger.error("Invalid UUID format for student_id in session: %s", student_id_str)
                flash('Invalid user session ID format.', 'error')
                return redirect(url_for('auth.login'))
        
        if not current_student:
             logger.error("Student profile not found in DB for session ID: %s", student_id_str)
             flash('Student profile not found. Please log in again.', 'error')
             return redirect(url_for('auth.login'))

        # Prepare base profile data
        safe_context['profile'] = {
            'name': current_student.full_name,
            'student_id': current_student.student_id,
            'program': current_student.program,
            'section': current_student.section,
            'email': current_student.email
        }
        
        # Check if survey is active
        survey_status = SurveyStatus.query.get(1)
        is_survey_active = survey_status.is_active if survey_status else False
        safe_context['survey_active'] = is_survey_active
        
        # Check if student has already submitted evaluation
        has_submitted = SurveySession.query.filter_by(student_uuid=current_student.id).first() is not None
        safe_context['evaluation_complete'] = has_submitted

        # Parse student's section (handle BSCS-2A format)
        student_full_section = current_student.section  # e.g., "BSCS-2A"
        if '-' in student_full_section:
            student_program, student_section = student_full_section.split('-', 1)
        else:
            student_program = current_student.program
            student_section = student_full_section
        
        # Get teachers assigned to the student's section (teaching staff)
        teaching_staff = Teacher.query.join(
            Teacher.sections_assigned
        ).join(
            Section.department
        ).filter(
            Section.name == student_section,
            Department.name == student_program
        ).options(
            db.joinedload(Teacher.departments_assigned),
            db.joinedload(Teacher.sections_assigned)
        ).all()
        
        # Get all non-teaching staff (all students evaluate non-teaching staff)
        non_teaching_staff = Teacher.query.join(
            Teacher.departments_assigned
        ).filter(
            Department.name == 'Admin'
        ).options(
            db.joinedload(Teacher.departments_assigned),
            db.joinedload(Teacher.sections_assigned)
        ).all()
        
        # Combine teaching and non-teaching staff
        safe_context['my_teachers'] = teaching_staff + non_teaching_staff
        
        # Always load questions from active survey
        active_survey = Survey.query.filter_by(is_active=True).first()
        if active_survey:
            safe_context['questions'] = Question.query.filter_by(survey_id=active_survey.id).all()
        elif not safe_context['questions']:
            # Fallback to any survey for display
            any_survey = Survey.query.first()
            if any_survey:
                safe_context['questions'] = Question.query.filter_by(survey_id=any_survey.id).all()
        
        # Handle survey states and load previous data if needed
        if is_survey_active:
            if not has_submitted:
                safe_context['can_submit'] = True
                safe_context['show_form'] = True
            else:
                safe_context['can_submit'] = False
                safe_context['review_mode'] = True
                safe_context['show_form'] = True
        else:
            if has_submitted:
                safe_context['can_submit'] = False
                safe_context['review_mode'] = True
                safe_context['show_form'] = True
                safe_context['survey_closed_message'] = 'The survey is now closed, but you can review your previous responses below.'
            else:
                safe_context['can_submit'] = False
                safe_context['review_mode'] = False
                safe_context['show_form'] = False
                safe_context['survey_closed_message'] = 'The survey is currently closed.'
        
        # Load previous comments if in review mode
        if safe_context['review_mode'] and has_submitted:
            existing_session = SurveySession.query.filter_by(student_uuid=current_student.id).first()
            if existing_session:
                safe_context['previous_comments'] = StudentComment.query.filter_by(session_id=existing_session.session_id).all()
            else:
                safe_context['previous_comments'] = []
        
        # Get published rankings
        ranking_status = RankingStatus.query.first()
        logger.info(f"Ranking status: {ranking_status}")
        if ranking_status:
            logger.info(f"is_posted_teaching: {ranking_status.is_posted_teaching}")
        
        if ranking_status and ranking_status.is_posted_teaching:
            # Get real rankings from app config
            published_data = current_app.config.get('PUBLISHED_RANKINGS', {})
            logger.info(f"Published data: {published_data}")
            safe_context['published_rankings'] = published_data.get('rankings', [])
            safe_context['rankings_posted'] = True
            logger.info(f"Rankings posted: True, count: {len(safe_context['published_rankings'])}")
        else:
            safe_context['published_rankings'] = []
            safe_context['rankings_posted'] = False
            logger.info("Rankings not posted or no ranking status found")
        
        return render_template('student.html', **safe_context)
        
    except Exception as e:
        logger.error("CRITICAL Student Home Error: %s", e)
        traceback.print_exc()
        flash('An internal error occurred loading the student dashboard.', 'error')
        return render_template('student.html', **safe_context)

@views.route('/api/departments/<uuid:department_id>/sections', methods=['GET'])
@admin_required
def get_sections_by_department(department_id):
    """API endpoint to fetch sections for a given department ID."""
    try:
        sections = Section.query.filter_by(department_id=department_id).all()
        sections_data = [{'id': str(s.id), 'name': s.name} for s in sections]
        return jsonify(sections_data)
    except Exception as e:
        logger.error(f"Error fetching sections for department {department_id}: {e}")
        return jsonify({'error': 'Failed to retrieve sections'}), 500

@views.route('/admin/reset_student/<student_id>', methods=['GET', 'POST'])
@admin_required
def reset_student_submission(student_id):
    """Reset a student's submission to allow resubmission"""
    try:
        student = Student.query.filter_by(student_id=student_id).first()
        if not student:
            flash('Student not found.', 'error')
            return redirect(url_for('views.admin_home'))
        
        # Delete existing session and answers
        existing_session = SurveySession.query.filter_by(student_uuid=student.id).first()
        if existing_session:
            Answer.query.filter_by(session_id=existing_session.session_id).delete()
            db.session.delete(existing_session)
            db.session.commit()
            flash(f'Reset submission for student {student_id}. They can now resubmit.', 'success')
        else:
            flash(f'No submission found for student {student_id}.', 'info')
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error resetting student submission: {e}")
        flash('Error resetting submission.', 'error')
    
    return redirect(url_for('views.admin_home'))

@views.route('/api/teacher/<uuid:teacher_id>', methods=['GET'])
@admin_required
def get_teacher_details(teacher_id):
    """API endpoint to fetch details for a specific teacher."""
    try:
        teacher = Teacher.query.options(
            db.joinedload(Teacher.departments_assigned),
            db.joinedload(Teacher.sections_assigned)
        ).get(teacher_id)

        if not teacher:
            return jsonify({'error': 'Teacher not found'}), 404

        # Get department names
        department_names = [d.name for d in teacher.departments_assigned]
        
        # Get section values in DEPARTMENT-SECTION format
        section_values = []
        for section in teacher.sections_assigned:
            dept_name = section.department.name if section.department else 'Unknown'
            section_values.append(f"{dept_name}-{section.name}")

        teacher_data = {
            'id': str(teacher.id),
            'name': teacher.name,
            'email': teacher.email,
            'image_url': teacher.image_url,
            'departments': department_names,
            'sections': section_values
        }
        return jsonify(teacher_data)
    except Exception as e:
        logger.error(f"Error fetching teacher details for {teacher_id}: {e}")
        return jsonify({'error': 'Failed to retrieve teacher details'}), 500

# Department and Section Management Routes
@views.route('/api/departments', methods=['GET'])
@admin_required
def get_all_departments():
    """Get all departments with their sections."""
    try:
        departments = Department.query.all()
        result = []
        for dept in departments:
            sections = Section.query.filter_by(department_id=dept.id).all()
            result.append({
                'id': str(dept.id),
                'name': dept.name,
                'sections': [{'id': str(s.id), 'name': s.name} for s in sections]
            })
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error fetching departments: {e}")
        return jsonify({'error': 'Failed to retrieve departments'}), 500

@views.route('/departments', methods=['POST'])
@admin_required
def create_department():
    """Create a new department."""
    try:
        data = request.get_json()
        name = data.get('name', '').strip()
        
        if not name:
            return jsonify({'status': 'error', 'message': 'Department name is required'}), 400
        
        # Check for duplicate
        existing = Department.query.filter_by(name=name).first()
        if existing:
            return jsonify({'status': 'error', 'message': 'Department already exists'}), 400
        
        department = Department(name=name)
        db.session.add(department)
        db.session.commit()
        
        return jsonify({
            'status': 'success',
            'message': 'Department created successfully',
            'department': {'id': str(department.id), 'name': department.name}
        })
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error creating department: {e}")
        return jsonify({'status': 'error', 'message': 'Failed to create department'}), 500

@views.route('/departments/<uuid:dept_id>', methods=['PUT'])
@admin_required
def update_department(dept_id):
    """Update a department."""
    try:
        data = request.get_json()
        name = data.get('name', '').strip()
        
        if not name:
            return jsonify({'status': 'error', 'message': 'Department name is required'}), 400
        
        department = Department.query.get(dept_id)
        if not department:
            return jsonify({'status': 'error', 'message': 'Department not found'}), 404
        
        # Check for duplicate (excluding current)
        existing = Department.query.filter(Department.name == name, Department.id != dept_id).first()
        if existing:
            return jsonify({'status': 'error', 'message': 'Department name already exists'}), 400
        
        department.name = name
        db.session.commit()
        
        return jsonify({
            'status': 'success',
            'message': 'Department updated successfully',
            'department': {'id': str(department.id), 'name': department.name}
        })
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error updating department: {e}")
        return jsonify({'status': 'error', 'message': 'Failed to update department'}), 500

@views.route('/departments/<uuid:dept_id>', methods=['DELETE'])
@admin_required
def delete_department(dept_id):
    """Delete a department if it has no dependencies."""
    try:
        department = Department.query.get(dept_id)
        if not department:
            return jsonify({'status': 'error', 'message': 'Department not found'}), 404
        
        # Check for assigned teachers
        teacher_count = len(department.teachers)
        # Check for sections
        section_count = Section.query.filter_by(department_id=dept_id).count()
        
        if teacher_count > 0:
            return jsonify({
                'status': 'error', 
                'message': f'Cannot delete department with {teacher_count} assigned teacher(s). Please reassign or remove teachers first.'
            }), 400
            
        if section_count > 0:
            return jsonify({
                'status': 'error', 
                'message': f'Cannot delete department with {section_count} section(s). Please delete sections first.'
            }), 400
        
        db.session.delete(department)
        db.session.commit()
        
        return jsonify({'status': 'success', 'message': 'Department deleted successfully'})
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error deleting department: {e}")
        return jsonify({'status': 'error', 'message': 'Failed to delete department'}), 500

@views.route('/sections', methods=['POST'])
@admin_required
def create_section():
    """Create a new section."""
    try:
        data = request.get_json()
        name = data.get('name', '').strip()
        department_id = data.get('department_id')
        
        if not name or not department_id:
            return jsonify({'status': 'error', 'message': 'Section name and department are required'}), 400
        
        try:
            dept_uuid = uuid.UUID(department_id)
        except ValueError:
            return jsonify({'status': 'error', 'message': 'Invalid department ID'}), 400
        
        department = Department.query.get(dept_uuid)
        if not department:
            return jsonify({'status': 'error', 'message': 'Department not found'}), 404
        
        # Check for duplicate within department
        existing = Section.query.filter_by(name=name, department_id=dept_uuid).first()
        if existing:
            return jsonify({'status': 'error', 'message': 'Section already exists in this department'}), 400
        
        section = Section(name=name, department_id=dept_uuid)
        db.session.add(section)
        db.session.commit()
        
        return jsonify({
            'status': 'success',
            'message': 'Section created successfully',
            'section': {
                'id': str(section.id), 
                'name': section.name, 
                'department_name': department.name
            }
        })
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error creating section: {e}")
        return jsonify({'status': 'error', 'message': 'Failed to create section'}), 500

@views.route('/sections/<uuid:section_id>', methods=['PUT'])
@admin_required
def update_section(section_id):
    """Update a section."""
    try:
        data = request.get_json()
        name = data.get('name', '').strip()
        
        if not name:
            return jsonify({'status': 'error', 'message': 'Section name is required'}), 400
        
        section = Section.query.get(section_id)
        if not section:
            return jsonify({'status': 'error', 'message': 'Section not found'}), 404
        
        # Check for duplicate within department (excluding current)
        existing = Section.query.filter(
            Section.name == name, 
            Section.department_id == section.department_id,
            Section.id != section_id
        ).first()
        if existing:
            return jsonify({'status': 'error', 'message': 'Section name already exists in this department'}), 400
        
        section.name = name
        db.session.commit()
        
        return jsonify({
            'status': 'success',
            'message': 'Section updated successfully',
            'section': {
                'id': str(section.id), 
                'name': section.name, 
                'department_name': section.department.name
            }
        })
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error updating section: {e}")
        return jsonify({'status': 'error', 'message': 'Failed to update section'}), 500

@views.route('/sections/<uuid:section_id>', methods=['DELETE'])
@admin_required
def delete_section(section_id):
    """Delete a section if it has no dependencies."""
    try:
        section = Section.query.get(section_id)
        if not section:
            return jsonify({'status': 'error', 'message': 'Section not found'}), 404
        
        # Check for dependencies
        if section.teachers:
            return jsonify({
                'status': 'error', 
                'message': 'Cannot delete section with assigned teachers'
            }), 400
        
        db.session.delete(section)
        db.session.commit()
        
        return jsonify({'status': 'success', 'message': 'Section deleted successfully'})
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error deleting section: {e}")
        return jsonify({'status': 'error', 'message': 'Failed to delete section'}), 500


@views.route('/test-forgot', methods=['GET', 'POST'])
def test_forgot():
    return jsonify({'message': 'Route is working', 'method': request.method})

@views.route('/forgot-password', methods=['POST'])
def forgot_password():
    """Handle forgot password requests for both staff and students."""
    try:
        data = request.get_json()
        email = data.get('email', '').strip().lower()
        user_type = data.get('user_type', 'student')
        
        if not email:
            return jsonify({'success': False, 'message': 'Email is required'}), 400
        
        user = None
        user_name = None
        
        if user_type == 'staff':
            from .models import User
            user = User.query.filter_by(email=email).first()
            if user:
                user_name = user.name
        else:
            user = Student.query.filter_by(email=email).first()
            if user:
                user_name = user.full_name
            else:
                import csv
                import os
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

@views.route('/reset-password', methods=['POST'])
def reset_password():
    """Reset password after OTP verification."""
    try:
        from werkzeug.security import generate_password_hash
        
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
            from .models import User
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
                import os
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

@views.route('/admin/update-profile', methods=['POST'])
@admin_required
def update_admin_profile():
    """Update admin profile information."""
    try:
        from .models import User
        
        user_id = session.get('user_id')
        user = User.query.get(uuid.UUID(user_id))
        
        if not user:
            return jsonify({'status': 'error', 'message': 'User not found'}), 404
        
        first_name = request.form.get('firstName', '').strip()
        last_name = request.form.get('lastName', '').strip()
        email = request.form.get('email', '').strip()
        
        if not all([first_name, last_name, email]):
            return jsonify({'status': 'error', 'message': 'All fields are required'}), 400
        
        # Check if email is already taken by another user
        existing_user = User.query.filter(User.email == email, User.id != user.id).first()
        if existing_user:
            return jsonify({'status': 'error', 'message': 'Email already in use'}), 400
        
        # Update user information
        user.name = f"{first_name} {last_name}"
        user.email = email
        
        db.session.commit()
        
        # Update session data
        session['user_name'] = user.name
        
        return jsonify({'status': 'success', 'message': 'Profile updated successfully'})
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error updating admin profile: {e}")
        return jsonify({'status': 'error', 'message': 'Error updating profile'}), 500

@views.route('/admin/update-password', methods=['POST'])
@admin_required
def update_admin_password():
    """Update admin password."""
    try:
        from werkzeug.security import check_password_hash, generate_password_hash
        from .models import User
        
        user_id = session.get('user_id')
        user = User.query.get(uuid.UUID(user_id))
        
        if not user:
            return jsonify({'status': 'error', 'message': 'User not found'}), 404
        
        current_password = request.form.get('current_password', '')
        new_password = request.form.get('new_password', '')
        
        if not all([current_password, new_password]):
            return jsonify({'status': 'error', 'message': 'All fields are required'}), 400
        
        # Verify current password
        if not check_password_hash(user.password_hash, current_password):
            return jsonify({'status': 'error', 'message': 'Current password is incorrect'}), 400
        
        if len(new_password) < 6:
            return jsonify({'status': 'error', 'message': 'New password must be at least 6 characters'}), 400
        
        # Update password
        user.password_hash = generate_password_hash(new_password, method='pbkdf2:sha256')
        db.session.commit()
        
        return jsonify({'status': 'success', 'message': 'Password updated successfully'})
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error updating admin password: {e}")
        return jsonify({'status': 'error', 'message': 'Error updating password'}), 500

@views.route('/admin/update-photo', methods=['POST'])
@admin_required
def update_admin_photo():
    """Update admin profile photo."""
    try:
        from .models import User
        
        user_id = session.get('user_id')
        user = User.query.get(uuid.UUID(user_id))
        
        if not user:
            return jsonify({'status': 'error', 'message': 'User not found'}), 404
        
        if 'photo' not in request.files:
            return jsonify({'status': 'error', 'message': 'No photo uploaded'}), 400
        
        file = request.files['photo']
        if file.filename == '':
            return jsonify({'status': 'error', 'message': 'No photo selected'}), 400
        
        if file and file.filename:
            # Save the uploaded file
            photo_url = save_uploaded_file(file, 'admin')
            if photo_url:
                # For now, we'll just return success since User model doesn't have image_url field
                # In a real implementation, you'd add an image_url field to User model
                return jsonify({'status': 'success', 'message': 'Photo uploaded successfully', 'photo_url': photo_url})
            else:
                return jsonify({'status': 'error', 'message': 'Error saving photo'}), 500
        
        return jsonify({'status': 'error', 'message': 'Invalid file'}), 400
        
    except Exception as e:
        logger.error(f"Error updating admin photo: {e}")
        return jsonify({'status': 'error', 'message': 'Error uploading photo'}), 500

@views.route('/submit_evaluation', methods=['POST'])
@login_required
def submit_evaluation():
    try:
        # Check if the global survey status is active
        survey_status_obj = SurveyStatus.query.get(1)
        if not survey_status_obj or not survey_status_obj.is_active:
            flash('The evaluation period is currently inactive. You cannot submit evaluations.', 'error')
            return redirect(url_for('views.student_home'))

        if session.get('user_role') != 'student':
            flash('Access denied.', 'error')
            return redirect(url_for('auth.login'))
        
        student_id_str = session.get('user_id')
        student_uuid = uuid.UUID(student_id_str)

        existing_session = SurveySession.query.filter_by(student_uuid=student_uuid).first()
        if existing_session:
            # Delete existing answers to allow resubmission
            Answer.query.filter_by(session_id=existing_session.session_id).delete()
            db.session.delete(existing_session)
            db.session.commit()
            logger.info(f"Reset existing submission for student {student_id_str}")

        # Get active survey
        active_survey = Survey.query.filter_by(is_active=True).first()
        if not active_survey:
            flash('No active survey found.', 'error')
            return redirect(url_for('views.student_home'))

        new_session = SurveySession(
            student_uuid=student_uuid, 
            survey_id=active_survey.id,
            survey_title=active_survey.title, 
            submission_date=datetime.utcnow()
        )
        db.session.add(new_session)
        db.session.flush()

        # Group answers by question to store multiple teacher scores per question
        question_answers = {}
        for key, value in request.form.items():
            if key.startswith('score_'):
                try:
                    _, teacher_id_str, question_id_str = key.split('_')
                    score = int(value)
                    question_uuid = uuid.UUID(question_id_str)
                    
                    if question_uuid not in question_answers:
                        question_answers[question_uuid] = []
                    
                    question_answers[question_uuid].append(f"{score}|{teacher_id_str}")

                except ValueError as ve:
                    logger.error("Malformed form key/value: %s=%s, Error: %s", key, value, ve)
                    continue
                except Exception as e:
                    logger.error("Error processing answer for key %s: %s", key, e)
                    continue
        
        # Create one answer per question with all teacher scores combined
        answers_to_add = []
        for question_uuid, teacher_scores in question_answers.items():
            combined_response = ";".join(teacher_scores)  # Combine multiple teacher scores
            answer = Answer(
                session_id=new_session.session_id,
                question_identifier=question_uuid,
                response_value=combined_response,
                survey_id=active_survey.id
            )
            answers_to_add.append(answer)

        if answers_to_add:
            try:
                db.session.add_all(answers_to_add)
                
                # Handle comments submission
                comments_added = 0
                for key, value in request.form.items():
                    if key.startswith('comment_') and value.strip():
                        try:
                            teacher_id_str = key.replace('comment_', '')
                            teacher_uuid = uuid.UUID(teacher_id_str)
                            
                            # Create comment record
                            comment = StudentComment(
                                session_id=new_session.session_id,
                                teacher_id=teacher_uuid,
                                comment_text=value.strip()
                            )
                            db.session.add(comment)
                            comments_added += 1
                            
                        except ValueError as ve:
                            logger.warning(f"Invalid teacher ID in comment: {teacher_id_str}, Error: {ve}")
                            continue
                        except Exception as e:
                            logger.error(f"Error processing comment for teacher {teacher_id_str}: {e}")
                            continue
                
                db.session.commit()
                
                if comments_added > 0:
                    flash(f'✅ Your evaluation and {comments_added} comment(s) have been submitted successfully!', 'success')
                else:
                    flash('✅ Your evaluation has been submitted successfully!', 'success')
                    
            except Exception as commit_error:
                db.session.rollback()
                logger.error(f"Database commit error: {commit_error}")
                logger.error(f"Session data: student_uuid={student_uuid}, survey_id={active_survey.id}")
                logger.error(f"Answers count: {len(answers_to_add)}")
                logger.error(f"Session ID: {new_session.session_id}")
                for i, answer in enumerate(answers_to_add):
                    logger.error(f"Answer {i}: session_id={answer.session_id}, question_id={answer.question_identifier}, response={answer.response_value}")
                flash('Database error during submission. Please try again.', 'error')
        else:
            db.session.rollback()
            flash('⚠️ No valid answers were recorded. Please ensure all fields are filled.', 'warning')

    except Exception as e:
        db.session.rollback()
        logger.error("SUBMISSION ERROR: %s", e)
        traceback.print_exc()
        flash('An internal error prevented submission. Please try again.', 'error')
        
    return redirect(url_for('views.student_home'))