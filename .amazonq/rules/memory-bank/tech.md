# Technology Stack

## Programming Languages
- **Python 3.x** - Primary backend language
- **HTML5** - Frontend markup with Jinja2 templating
- **CSS3** - Styling with responsive design and dark/light themes
- **JavaScript (ES6+)** - Client-side interactivity and AJAX

## Core Framework & Libraries
- **Flask** - Lightweight web framework
- **SQLAlchemy** - ORM for database operations
- **Flask-Login** - User session management
- **Werkzeug** - Password hashing and security utilities
- **Jinja2** - Template engine for dynamic HTML rendering

## Database Systems
- **PostgreSQL** - Primary production database
- **SQLite** - Development and testing database
- **CSV** - Data import/export format

## Frontend Technologies
- **Responsive CSS** - Mobile-first design approach
- **Vanilla JavaScript** - No external JS frameworks
- **Canvas API** - Chart rendering for analytics
- **Local Storage** - Theme preferences and client-side data

## Development Tools & Configuration
- **python-dotenv** - Environment variable management
- **WSGI** - Production deployment interface
- **CSV Module** - Data processing and bulk imports

## Environment Configuration
```
POSTGRES_USER=postgres
POSTGRES_PASS=your_password
POSTGRES_DB=pgpc_sis_db
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
FLASK_ENV=development
```

## Development Commands
- **Start Development Server**: `python run.py`
- **Database Migration**: `python migrate_db.py`
- **Ranking Migration**: `python migrate_ranking.py`
- **Production Deployment**: Use `wsgi.py` with WSGI server

## Security Features
- **PBKDF2-SHA256** password hashing
- **Session management** with Flask-Login
- **CSRF protection** through secure session cookies
- **Role-based access control** (admin/student roles)
- **HTTP security headers** (no-cache, secure cookies)

## Email Integration
- **SMTP support** for automated reminders
- **Gmail integration** with app passwords
- **Configurable email templates** and utilities