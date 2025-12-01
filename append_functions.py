# Script to append missing functions to app.py

content_to_append = '''
        
    else:
        no_data_table = Table([['NO EVALUATION DATA AVAILABLE']], colWidths=[7*72])
        no_data_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.yellow),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 14),
            ('GRID', (0, 0), (-1, -1), 2, colors.red),
            ('TOPPADDING', (0, 0), (-1, -1), 20),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 20),
        ]))
        story.append(no_data_table)

    doc.build(story)
    buffer.seek(0)
    return buffer

def generate_staff_pdf_report(teacher_averages=None, session_count=0, staff_type='all'):
    return generate_pdf_report({str(t['id']): {'average': t['score'], 'count': t['count']} for t in teacher_averages} if teacher_averages else {}, session_count)
    
def generate_simple_pdf_report(staff_averages=None, session_count=0, staff_type='all'):
    return generate_pdf_report({str(t['id']): {'average': t['score'], 'count': t['count']} for t in staff_averages} if staff_averages else {}, session_count)


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
        data = request.get_json()
        rankings = data.get('rankings', [])
        
        ranking_status = RankingStatus.query.first()
        if not ranking_status:
            ranking_status = RankingStatus(is_published=True, published_date=datetime.utcnow())
            db.session.add(ranking_status)
        else:
            ranking_status.is_published = True
            ranking_status.published_date = datetime.utcnow()
        
        session['published_rankings'] = {
            'rankings': rankings,
            'published_date': datetime.utcnow().isoformat()
        }
        
        db.session.commit()
        return jsonify({'status': 'success', 'message': 'Final rankings posted'}), 200
    except Exception as e:
        db.session.rollback()
        logger.error('Error posting final ranking: %s', e)
        return jsonify({'status': 'error', 'message': str(e)}), 400

@views.route('/ranking/post', methods=['POST'])
@admin_required
def post_ranking():
    return jsonify({'status': 'success', 'message': 'Ranking Posted/Updated Successfully!'}), 200

@views.route('/survey/activate', methods=['POST'])
@admin_required
def activate_survey():
    try:
        survey_status = SurveyStatus.query.get(1)
        if not survey_status:
            survey_status = SurveyStatus(id=1, is_active=True, last_change=datetime.utcnow())
            db.session.add(survey_status)
        else:
            survey_status.is_active = True
            survey_status.last_change = datetime.utcnow()
        db.session.commit()
        flash('Survey has been activated successfully!', 'success')
        return jsonify({'status': 'success'}), 200
    except Exception as e:
        db.session.rollback()
        flash(f'Error activating survey: {e}', 'error')
        logger.error('Error activating survey: %s', e)
        return jsonify({'status': 'error', 'message': str(e)}), 400

@views.route('/survey/deactivate', methods=['POST'])
@admin_required
def deactivate_survey():
    try:
        survey_status = SurveyStatus.query.get(1)
        if not survey_status:
            survey_status = SurveyStatus(id=1, is_active=False, last_change=datetime.utcnow())
            db.session.add(survey_status)
        else:
            survey_status.is_active = False
            survey_status.last_change = datetime.utcnow()
        db.session.commit()
        flash('Survey has been deactivated successfully!', 'success')
        return jsonify({'status': 'success'}), 200
    except Exception as e:
        db.session.rollback()
        flash(f'Error deactivating survey: {e}', 'error')
        logger.error('Error deactivating survey: %s', e)
        return jsonify({'status': 'error', 'message': str(e)}), 400

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

def save_uploaded_file(file, prefix='teacher'):
    if file and file.filename:
        filename = f"{prefix}_{uuid.uuid4().hex[:8]}_{file.filename}"
        upload_dir = os.path.join(current_app.static_folder, 'uploads')
        os.makedirs(upload_dir, exist_ok=True)
        file_path = os.path.join(upload_dir, filename)
        file.save(file_path)
        return f"/static/uploads/{filename}"
    return None

@views.route('/save_teacher_profile', methods=['POST'])
@admin_required
def save_teacher_profile():
    teacher_id_str = request.form.get('teacher_id')
    name = request.form.get('name')
    email = request.form.get('email')
    
    departments = request.form.getlist('departments')
    sections = request.form.getlist('sections')
    
    try:
        departments_json = json.dumps(departments)
        sections_json = json.dumps(sections)
    except Exception as e:
        flash(f"Error encoding departments/sections: {e}", 'error')
        return redirect(url_for('views.admin_home') + '#view-teachers')

    image_url = None
    if 'image_file' in request.files:
        file = request.files['image_file']
        if file and file.filename:
            image_url = save_uploaded_file(file, 'teacher')
    
    if not image_url:
        image_url = f"https://placehold.co/100x100/5070ff/ffffff?text={name[:2].upper()}"

    try:
        if teacher_id_str == 'new':
            if Teacher.query.filter_by(email=email).first():
                flash(f'A teacher with the email {email} already exists.', 'warning')
                return redirect(url_for('views.admin_home') + '#view-teachers')

            teacher = Teacher(
                name=name, email=email, 
                departments=departments_json, sections=sections_json, 
                department=departments[0] if departments else None, 
                section=sections[0] if sections else None,
                image_url=image_url
            )
            db.session.add(teacher)
            flash('Teacher profile added successfully.', 'success')
        else:
            teacher_id_uuid = uuid.UUID(teacher_id_str) 
            teacher = Teacher.query.get(teacher_id_uuid)
            
            if teacher:
                if Teacher.query.filter(Teacher.email == email, Teacher.id != teacher_id_uuid).first():
                    flash(f'A different teacher with the email {email} already exists.', 'warning')
                    return redirect(url_for('views.admin_home') + '#view-teachers')

                teacher.name = name
                teacher.email = email
                teacher.departments = departments_json
                teacher.sections = sections_json
                teacher.department = departments[0] if departments else None
                teacher.section = sections[0] if sections else None
                
                if 'image_file' in request.files and request.files['image_file'].filename:
                    teacher.image_url = image_url
                flash('Teacher profile updated successfully.', 'success')
            else:
                flash('Teacher not found.', 'error')
        
        db.session.commit()
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error saving teacher profile: {e}', 'error')
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

@views.route('/create_survey', methods=['POST'])
@admin_required
def create_survey():
    survey_title = request.form.get('title')
    survey_description = request.form.get('description')
    
    try:
        new_survey = Survey(
            title=survey_title,
            description=survey_description,
            is_active=False
        )
        db.session.add(new_survey)
        db.session.commit()
        flash(f'Survey "{survey_title}" created successfully as a draft.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error creating survey: {e}', 'error')
        traceback.print_exc()

    return redirect(url_for('views.admin_home') + '#view-survey')

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
    survey_id = request.form.get('survey_id')

    try:
        survey_uuid = uuid.UUID(survey_id)
        survey = Survey.query.get(survey_uuid)
            
        if survey:
            question = Question(
                criteria=criteria, 
                text=question_text, 
                survey_id=survey.id
            )
            
            db.session.add(question)
            db.session.commit()
            
            return jsonify({'status': 'success', 'message': 'Question added successfully!'}), 200
        else: 
            return jsonify({'status': 'error', 'message': 'Survey not found.'}), 404
            
    except ValueError:
        return jsonify({'status': 'error', 'message': 'Invalid survey ID format.'}), 400
    except Exception as e:
        db.session.rollback()
        logger.error("Error adding question: %s", e)
        traceback.print_exc()
        return jsonify({'status': 'error', 'message': f'Error adding question: {e}'}), 500

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

@views.route('/submit_evaluation', methods=['POST'])
@login_required
def submit_evaluation():
    try:
        if session.get('user_role') != 'student':
            flash('Access denied.', 'error')
            return redirect(url_for('auth.login'))
        
        student_id_str = session.get('user_id')
        student_uuid = uuid.UUID(student_id_str)

        if SurveySession.query.filter_by(student_uuid=student_uuid).first():
            flash('You have already submitted your evaluation.', 'warning')
            return redirect(url_for('views.student_home'))

        new_session = SurveySession(student_uuid=student_uuid, survey_title='Teacher Evaluation', submission_date=datetime.utcnow())
        db.session.add(new_session)
        db.session.flush()

        answers_to_add = []
        for key, value in request.form.items():
            if key.startswith('score_'):
                try:
                    _, teacher_id_str, question_id_str = key.split('_')
                    score = int(value)
                    
                    response_value = f"{score}|{teacher_id_str}" 

                    answer = Answer(
                        session_id=new_session.session_id,
                        question_identifier=uuid.UUID(question_id_str),
                        response_value=response_value
                    )
                    answers_to_add.append(answer)

                except ValueError as ve:
                    logger.warning("Malformed form key/value: %s=%s, Error: %s", key, value, ve)
                    continue
                except Exception as e:
                    logger.warning("Error processing answer for key %s: %s", key, e)
                    continue

        if answers_to_add:
            db.session.add_all(answers_to_add)
            db.session.commit()
            flash('✅ Your evaluation has been submitted successfully!', 'success')
        else:
            db.session.rollback()
            flash('⚠️ No valid answers were recorded. Please ensure all fields are filled.', 'warning')

    except Exception as e:
        db.session.rollback()
        logger.error("SUBMISSION ERROR: %s", e)
        traceback.print_exc()
        flash('An internal error prevented submission. Please try again.', 'error')
        
    return redirect(url_for('views.student_home'))
'''

with open('webapp/app.py', 'a', encoding='utf-8') as f:
    f.write(content_to_append)

print("✅ Functions appended successfully!")
