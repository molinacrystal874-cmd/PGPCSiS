# Development Guidelines

## Code Quality Standards

### Import Organization
- **Flask imports first**: Core Flask modules imported at the top
- **Third-party imports**: External libraries grouped together
- **Local imports**: Application modules imported last with relative imports (`.models`, `.database`)
- **Conditional imports**: Heavy libraries imported within functions when needed

### Error Handling Patterns
- **Try-catch blocks**: Comprehensive exception handling with database rollbacks
- **Flash messages**: User-friendly error messages with categorized types ('error', 'success', 'warning', 'info')
- **Debug logging**: Print statements for development debugging with descriptive prefixes
- **Graceful degradation**: Safe fallback objects to prevent template crashes

### Database Interaction Standards
- **Model prefixing**: Always use `models.ModelName` for clarity and avoiding circular imports
- **Session management**: Explicit `db.session.commit()` and `db.session.rollback()` in try-catch blocks
- **UUID handling**: Consistent UUID conversion with proper exception handling
- **Query patterns**: Use `.query.filter_by()` for simple queries, `.query.filter()` for complex conditions

## Architectural Patterns

### Blueprint Organization
- **Separation of concerns**: `auth` blueprint for authentication, `views` blueprint for main application logic
- **URL prefixes**: Both blueprints use '/' prefix for clean URLs
- **Route grouping**: Related functionality grouped within appropriate blueprints

### Decorator Usage
- **Authentication decorators**: `@login_required` for basic auth, `@admin_required` for role-based access
- **Response headers**: No-cache headers applied consistently in decorators
- **Wrapper functions**: `@wraps(f)` used to preserve function metadata

### Session Management
- **Flask-Login integration**: UserMixin inheritance for both User and Student models
- **Session data**: Structured session storage with user_id, user_name, user_role, user_section
- **Security**: Session clearing on logout and password changes

## Database Design Patterns

### Model Relationships
- **UUID primary keys**: All models use UUID for primary keys with `default=uuid.uuid4`
- **Foreign key relationships**: Proper SQLAlchemy relationships with backref
- **Legacy compatibility**: Maintaining old table structures while introducing new ones
- **Unique constraints**: Multi-column unique constraints for business logic enforcement

### Data Validation
- **Input sanitization**: `.strip()` on all form inputs
- **Type conversion**: Explicit UUID conversion with error handling
- **Range validation**: Score validation (1-5 range) with user feedback
- **Existence checks**: Database existence verification before operations

## Security Implementation

### Authentication Flow
- **Role-based access**: Separate login paths for staff and students
- **Password policies**: Minimum 6 characters, forced password changes for default passwords
- **Session security**: HTTPOnly cookies, secure session configuration
- **OTP verification**: Client-side OTP generation with server-side verification

### Data Protection
- **Password hashing**: PBKDF2-SHA256 for all password storage
- **Input validation**: Comprehensive form validation with error messages
- **SQL injection prevention**: SQLAlchemy ORM usage throughout
- **XSS protection**: Flash message categorization and proper template escaping

## Frontend Integration Patterns

### Template Data Passing
- **Context dictionaries**: Structured data passing to templates with fallback values
- **Safe defaults**: Mock objects to prevent template crashes on database errors
- **JSON serialization**: Proper JSON handling for AJAX responses
- **Error state handling**: Graceful error display in templates

### AJAX Communication
- **JSON responses**: Standardized response format with status and message fields
- **Error handling**: Consistent error response structure across endpoints
- **Form processing**: Mixed form and JSON data handling patterns
- **Client feedback**: Flash messages for user action confirmation

## Performance Considerations

### Database Optimization
- **Lazy loading**: Strategic use of `lazy='dynamic'` for large relationships
- **Query efficiency**: Filtering at database level rather than in Python
- **Batch operations**: Bulk inserts and updates where appropriate
- **Connection management**: Proper database connection handling in application factory

### Memory Management
- **File handling**: Proper file closure and cleanup in CSV processing
- **Session cleanup**: Explicit session clearing on logout
- **Buffer management**: BytesIO usage for PDF generation with proper cleanup
- **Import optimization**: Conditional imports for heavy libraries

## Testing and Debugging

### Debug Patterns
- **Descriptive logging**: Prefixed debug messages with context information
- **Exception tracing**: Full traceback printing in development mode
- **Data validation**: Debug output for data processing verification
- **State checking**: Session and database state verification

### Error Recovery
- **Database rollbacks**: Automatic rollback on exceptions
- **User feedback**: Clear error messages with actionable guidance
- **Fallback mechanisms**: Safe defaults when primary operations fail
- **Graceful degradation**: Partial functionality when components fail