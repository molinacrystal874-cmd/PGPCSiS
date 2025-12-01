# Fixes and Features Applied

This document details the changes made to the PGPCSiS application to implement the "Send Reminders" email system.

## 1. Send Reminders Button

A "Send Reminders" button has been added to the admin dashboard in `webapp/templates/admin.html`. This allows administrators to send email reminders to students who have not completed their evaluation surveys.

### `webapp/templates/admin.html`

```html
<!-- Completion by Department -->
<div class="bg-white p-6 rounded-lg shadow-sm dark:bg-gray-800">
    <h3 class="text-xl font-semibold text-gray-900 mb-4 dark:text-white">Completion by Department</h3>
    <p class="text-gray-600 mb-4 dark:text-gray-300">Send reminders to students by department who have not completed the survey.</p>
    <div class="flex items-center gap-4">
        <select id="program-filter" class="px-4 py-2 border border-gray-300 rounded-lg dark:bg-gray-700 dark:border-gray-600 dark:text-white">
            <option value="">All Programs</option>
            {% for program in mock_programs %}
            <option value="{{ program }}">{{ program }}</option>
            {% endfor %}
        </select>
        <button onclick="handleAction('send_reminders', '/email/send_reminder', 'Send Reminder Emails', { program_name: document.getElementById('program-filter').value })" class="px-5 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-colors duration-200 dark:hover:bg-purple-500">
            Send Reminders
        </button>
    </div>
</div>
```

## 2. Flask-Mail Configuration

The application is configured to use Flask-Mail with SMTP settings from the `.env` file. The configuration is located in `webapp/__init__.py`. No changes were required as the configuration was already in place.

### `webapp/__init__.py`

```python
# Email configuration
app.config['MAIL_SERVER'] = os.getenv('MAIL_SERVER', 'smtp.gmail.com')
app.config['MAIL_PORT'] = int(os.getenv('MAIL_PORT', 587))
app.config['MAIL_USE_TLS'] = os.getenv('MAIL_USE_TLS', 'True').lower() in ('true', '1', 't')
app.config['MAIL_USE_SSL'] = os.getenv('MAIL_USE_SSL', 'False').lower() in ('true', '1', 't')
app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')
app.config['MAIL_DEFAULT_SENDER'] = os.getenv('MAIL_USERNAME')

# ...

mail.init_app(app)
```

## 3. Email Template

A new email template, `reminder.html`, has been created for the reminder emails.

### `webapp/templates/email/reminder.html`

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Reminder: Please Complete Your Evaluation Survey</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            line-height: 1.6;
            color: #333;
        }
        .container {
            width: 80%;
            margin: 0 auto;
            padding: 20px;
            border: 1px solid #ddd;
            border-radius: 5px;
        }
        .header {
            text-align: center;
            margin-bottom: 20px;
        }
        .header h1 {
            margin: 0;
            font-size: 24px;
            color: #444;
        }
        .content p {
            margin-bottom: 15px;
        }
        .cta-button {
            display: inline-block;
            padding: 10px 20px;
            margin-top: 15px;
            background-color: #007bff;
            color: #fff;
            text-decoration: none;
            border-radius: 5px;
        }
        .footer {
            margin-top: 20px;
            text-align: center;
            font-size: 12px;
            color: #777;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Padre Garcia Polytechnic College</h1>
        </div>
        <div class="content">
            <p>Dear {{ student_name }},</p>
            <p>You still haven’t completed your evaluation survey.</p>
            <p>Please answer as soon as possible to avoid delays in processing results.</p>
            <a href="{{ evaluation_link }}" class="cta-button">Complete Evaluation</a>
        </div>
        <div class="footer">
            <p>Thank you – Padre Garcia Polytechnic College</p>
        </div>
    </div>
</body>
</html>
```

## 4. Backend Logic

The backend logic for sending reminders is implemented in the `send_reminder` function in `webapp/app.py`.

### `webapp/app.py`

```python
@views.route('/email/send_reminder', methods=['POST'])
@admin_required
def send_reminder():
    data = request.get_json(silent=True) or {}
    target_program = data.get('program_name')

    try:
        completed_student_ids = db.session.query(SurveySession.student_uuid).distinct().subquery()
        
        students_query = db.session.query(Student).filter(
            ~Student.id.in_(db.session.query(completed_student_ids.c.student_uuid))
        )

        if target_program:
            program_code = target_program.split('(')[-1].replace(')', '') if '(' in target_program else target_program
            students_query = students_query.filter(Student.program == program_code)
            
        students_to_remind = students_query.all()

        if not students_to_remind:
            program_msg = f" in {target_program}" if target_program else ""
            flash(f'All students{program_msg} have already submitted their evaluations.', 'info')
            return redirect(url_for('views.admin_home', _anchor='view-dashboard')) 

        sent_count = 0
        failed_count = 0
        
        with mail.connect() as conn:
            for student in students_to_remind:
                try:
                    msg = Message("Reminder: Please Complete Your Evaluation Survey",
                                  recipients=[student.email])
                    msg.html = render_template('email/reminder.html',
                                               student_name=student.full_name,
                                               evaluation_link=url_for('auth.login', _external=True))
                    conn.send(msg)
                    sent_count += 1
                    logger.info(f"Reminder sent to: {student.full_name} ({student.email})")
                except Exception as e:
                    failed_count += 1
                    logger.error(f"Failed to send reminder to: {student.full_name} ({student.email}) - {e}")

        program_suffix = f" in {target_program}" if target_program else ""
        
        if sent_count > 0:
            flash(f'✅ SUCCESS! Sent {sent_count} email reminders to students who have not completed evaluations{program_suffix}.', 'success')
        
        if failed_count > 0:
            flash(f'⚠️ {failed_count} emails failed to send. Check email configuration.', 'warning')
        
        if sent_count == 0 and failed_count == 0:
            flash('ℹ️ All students have completed their evaluations. No reminders needed.', 'info')
        
    except Exception as e:
        logger.error(f"An error occurred in send_reminder: {e}")
        flash('An unexpected error occurred while sending reminders.', 'error')

    return redirect(url_for('views.admin_home', _anchor='view-dashboard'))
```

The query to find students who have not answered is:

```python
completed_student_ids = db.session.query(SurveySession.student_uuid).distinct().subquery()

students_query = db.session.query(Student).filter(
    ~Student.id.in_(db.session.query(completed_student_ids.c.student_uuid))
)
```
