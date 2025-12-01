import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def send_reminder_email(student_email, student_name, program, section):
    """
    Send a reminder email to a student who hasn't completed their evaluation.
    
    Args:
        student_email (str): Student's email address
        student_name (str): Student's full name
        program (str): Student's program (e.g., BSCS)
        section (str): Student's section (e.g., BSCS-2A)
    
    Returns:
        bool: True if email was sent successfully, False otherwise
    """
    try:
        # Email configuration from environment variables
        smtp_server = os.getenv('MAIL_SERVER', 'smtp.gmail.com')
        smtp_port = int(os.getenv('MAIL_PORT', '587'))
        sender_email = os.getenv('MAIL_USERNAME')
        sender_password = os.getenv('MAIL_PASSWORD')
        
        if not sender_email or not sender_password:
            print("ERROR: Email credentials not configured in .env file")
            return False
        
        # Create message
        message = MIMEMultipart()
        message["From"] = sender_email
        message["To"] = student_email
        message["Subject"] = "Reminder: Complete Your Teacher Evaluation - PGPC"
        
        # Email body
        body = f"""
Dear {student_name},

This is a friendly reminder that you have not yet completed your teacher evaluation for this semester.

Student Details:
- Name: {student_name}
- Program: {program}
- Section: {section}

Please log in to the PGPC Student Information System to complete your evaluation as soon as possible.

Your feedback is important for improving the quality of education at Padre Garcia Polytechnic College.

Thank you for your cooperation.

Best regards,
PGPC Administration
        """
        
        message.attach(MIMEText(body, "plain"))
        
        # Send email
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(sender_email, sender_password)
            server.send_message(message)
        
        print(f"Reminder email sent successfully to {student_email}")
        return True
        
    except Exception as e:
        print(f"Failed to send email to {student_email}: {str(e)}")
        return False