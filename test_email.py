
import os
from flask import Flask
from flask_mail import Mail, Message
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

# Email configuration
app.config['MAIL_SERVER'] = os.getenv('MAIL_SERVER')
app.config['MAIL_PORT'] = int(os.getenv('MAIL_PORT'))
app.config['MAIL_USE_TLS'] = os.getenv('MAIL_USE_TLS', 'True').lower() in ('true', '1', 't')
app.config['MAIL_USE_SSL'] = os.getenv('MAIL_USE_SSL', 'False').lower() in ('true', '1', 't')
app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')
app.config['MAIL_DEFAULT_SENDER'] = os.getenv('MAIL_USERNAME')

mail = Mail(app)

def send_test_email():
    with app.app_context():
        try:
            msg = Message("Test Email from PGPCSiS",
                          recipients=["crystalyn079@gmail.com"])
            msg.body = "This is a test email to check the email functionality of the PGPCSiS application."
            mail.send(msg)
            print("Test email sent successfully!")
        except Exception as e:
            print(f"Failed to send test email: {e}")

if __name__ == '__main__':
    send_test_email()
