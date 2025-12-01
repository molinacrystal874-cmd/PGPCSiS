# Project Structure

## Directory Organization

### Root Level
- `run.py` - Application entry point and development server launcher
- `wsgi.py` - WSGI configuration for production deployment
- `migrate_db.py` - Database migration utilities
- `migrate_ranking.py` - Ranking system migration scripts
- `.env` / `.env.example` - Environment configuration templates

### Core Application (`webapp/`)
**Main Application Files:**
- `__init__.py` - Flask application factory and configuration
- `app.py` - Main application routes and business logic
- `auth.py` - Authentication and authorization handlers
- `models.py` - SQLAlchemy database models and relationships
- `database.py` - Database initialization and connection management

**Email Services:**
- `email_service.py` - Email sending functionality
- `email_utils.py` - Email utility functions and templates

### Data Layer (`webapp/data/`)
- `app.db` - SQLite database file
- `evaluations.json` - Evaluation data storage
- `questions.json` - Survey questions configuration
- `students_data.csv` - Student information import/export
- `survey_status.json` - Survey state management
- `teachers.json` - Teaching staff data

### Frontend (`webapp/templates/`)
- `base.html` - Base template with common layout
- `admin.html` - Administrative dashboard interface
- `student.html` - Student evaluation interface
- `login.html` - Authentication forms
- `*_results.html` - Results display templates
- `_footer.html` - Shared footer component

### Static Assets (`webapp/static/`)
- `style.css` - Application styling and responsive design
- `*.jpg`, `*.png` - Logo and background images

## Architectural Patterns

### MVC Architecture
- **Models**: SQLAlchemy ORM models in `models.py`
- **Views**: Jinja2 templates in `templates/`
- **Controllers**: Flask routes and logic in `app.py` and `auth.py`

### Component Relationships
- **Authentication Layer**: `auth.py` handles user sessions and role-based access
- **Data Access Layer**: `models.py` and `database.py` manage data persistence
- **Business Logic**: `app.py` contains evaluation calculations and survey management
- **Presentation Layer**: Templates with dynamic content rendering and AJAX interactions

### Database Design
- Relational model with foreign key relationships
- Separate entities for users, surveys, questions, and answers
- JSON storage for flexible configuration data