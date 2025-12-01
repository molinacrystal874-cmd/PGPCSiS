# PGPCSiS - Performance Grading and Performance Calculation System in Schools

A comprehensive web-based evaluation system for educational institutions to conduct systematic performance assessments of teaching and non-teaching staff.

## Features

- **Multi-Role Authentication**: Secure login system with role-based access (admin, student)
- **Dual Evaluation System**: Separate evaluation workflows for teaching and non-teaching staff
- **Survey Management**: Dynamic survey creation, editing, and management
- **Real-time Analytics**: Dashboard with response tracking and visual charts
- **Ranking System**: Automated calculation and display of staff performance rankings
- **Comments System**: Optional feedback from students with PDF report integration
- **Data Export**: Excel and PDF export functionality
- **Email Integration**: Automated reminder system
- **Responsive Design**: Mobile-friendly interface

## Deployment on Render

### Prerequisites
1. GitHub account
2. Render account (free tier available)

### Steps to Deploy

1. **Push to GitHub**:
   ```bash
   git init
   git add .
   git commit -m "Initial commit"
   git branch -M main
   git remote add origin https://github.com/yourusername/pgpcsis.git
   git push -u origin main
   ```

2. **Deploy on Render**:
   - Go to [render.com](https://render.com)
   - Click "New +" → "Web Service"
   - Connect your GitHub repository
   - Use these settings:
     - **Build Command**: `pip install -r requirements.txt`
     - **Start Command**: `gunicorn wsgi:app`
     - **Environment**: `Python 3`

3. **Add Database**:
   - In Render dashboard, click "New +" → "PostgreSQL"
   - Name it `pgpcsis-db`
   - Copy the connection string
   - In your web service, add environment variable:
     - `DATABASE_URL`: [paste connection string]

4. **Environment Variables**:
   Add these in Render dashboard:
   - `FLASK_ENV`: `production`
   - `DATABASE_URL`: [from PostgreSQL service]

## Local Development

1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Set Environment Variables**:
   Create `.env` file:
   ```
   POSTGRES_USER=postgres
   POSTGRES_PASS=your_password
   POSTGRES_DB=pgpc_sis_db
   POSTGRES_HOST=localhost
   POSTGRES_PORT=5432
   ```

3. **Run Application**:
   ```bash
   python run.py
   ```

## Default Login Credentials

- **Admin**: admin@pgpc.edu / adminpass
- **Student**: Use student ID from CSV file / student ID as password

## Tech Stack

- **Backend**: Flask, SQLAlchemy, PostgreSQL
- **Frontend**: HTML5, CSS3, JavaScript, Tailwind CSS
- **Authentication**: Flask-Login, Werkzeug
- **Reports**: ReportLab (PDF generation)
- **Deployment**: Render, Gunicorn