from webapp import create_app
from webapp.database import db

app = create_app()

with app.app_context():
    db.create_all()
    print("Database tables created successfully!")