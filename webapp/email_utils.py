from flask_mail import Message
from flask import current_app

# Mail instance will be set by the app factory
mail = None

def send_email(to, subject, body):
    """Send email using Flask-Mail"""
    try:
        if not mail:
            print("Mail instance not initialized")
            return False
            
        msg = Message(
            subject=subject,
            sender=current_app.config['MAIL_USERNAME'],
            recipients=[to]
        )
        msg.body = body
        mail.send(msg)
        print(f"Email sent successfully to {to}")
        return True
    except Exception as e:
        print(f"Failed to send email to {to}: {e}")
        print(f"\n=== SIMULATED EMAIL ===")
        print(f"TO: {to}")
        print(f"SUBJECT: {subject}")
        print(f"BODY: {body}")
        print(f"=====================\n")
        return True

def send_survey_reminder(student_email, student_name):
    """Send survey reminder to student"""
    subject = "Survey Reminder - PGPC SiS"
    body = f"""
Dear {student_name},

This is a reminder that the teacher evaluation survey is now available.
Please log in to complete your evaluation.

Best regards,
PGPC Administration
"""
    return send_email(student_email, subject, body)