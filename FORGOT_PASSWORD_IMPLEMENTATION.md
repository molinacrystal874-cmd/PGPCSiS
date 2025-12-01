# Forgot Password Implementation

## Overview
This implementation provides a comprehensive forgot password system that works with both database users (staff) and CSV-based students. The system handles the transition from CSV data to database records seamlessly.

## Features

### 1. Multi-User Support
- **Staff Users**: Stored in the database `users` table
- **Database Students**: Stored in the database `students` table  
- **CSV Students**: Initially stored in `students_data.csv`, automatically migrated to database

### 2. Security Features
- **OTP Verification**: 6-digit codes sent via email
- **Session-based OTP Storage**: Secure server-side verification
- **Password Requirements**: Minimum 6 characters
- **Automatic Database Migration**: CSV students are moved to database on first password reset

### 3. User Experience
- **Two-step Process**: Email verification → Password reset
- **Real-time Validation**: Client-side and server-side validation
- **Clear Error Messages**: User-friendly feedback
- **Responsive Design**: Works on all devices

## Technical Implementation

### Backend Routes

#### `/forgot-password` (POST)
Handles initial password reset requests:
```python
{
    "email": "user@example.com",
    "user_type": "staff" | "student"
}
```

**Process:**
1. Validates email format and presence
2. Searches for user in appropriate data source:
   - Staff: `users` table
   - Students: `students` table → `students_data.csv` (fallback)
3. Generates 6-digit OTP and stores in session
4. Returns OTP for email sending

#### `/reset-password` (POST)
Handles password reset after OTP verification:
```python
{
    "email": "user@example.com",
    "otp_code": "123456",
    "new_password": "newpassword123"
}
```

**Process:**
1. Validates OTP against session-stored value
2. Validates password requirements
3. Updates password in database:
   - Staff: Updates `users` table
   - Database Students: Updates `students` table
   - CSV Students: Creates new record in `students` table
4. Clears session data

### Frontend Integration

#### Email Service (EmailJS)
- Service ID: `service_08d79rj`
- Template ID: `template_ct34lg4`
- Sends OTP codes to user email addresses

#### Modal Interface
- **Step 1**: Email input and verification code sending
- **Step 2**: OTP verification and password reset
- **Validation**: Real-time form validation
- **Error Handling**: User-friendly error messages

### Database Schema Updates

#### Students Table
```sql
ALTER TABLE students ADD COLUMN password_changed BOOLEAN DEFAULT FALSE;
```

This column tracks whether students have changed their default password.

## CSV to Database Migration

### Automatic Migration Process
1. **Login Attempt**: Student tries to log in with Student ID
2. **Database Check**: System checks `students` table first
3. **CSV Fallback**: If not found, checks `students_data.csv`
4. **Account Creation**: Creates database record with default password (Student ID)
5. **Password Reset**: When student uses forgot password, account is fully migrated

### Data Consistency
- **Primary Source**: Database becomes the authoritative source
- **CSV Backup**: Original CSV remains for reference
- **No Duplicates**: System prevents duplicate accounts

## Security Considerations

### OTP Security
- **6-digit codes**: Balance between security and usability
- **Session storage**: Server-side verification prevents tampering
- **Time-limited**: OTP expires when session ends
- **Single-use**: OTP is cleared after successful reset

### Password Security
- **Hashing**: PBKDF2-SHA256 for all passwords
- **Minimum length**: 6 characters required
- **Confirmation**: Double-entry validation
- **Force change**: Default passwords require immediate change

### Session Management
- **Isolated storage**: Each email gets separate session keys
- **Cleanup**: Session data cleared after successful reset
- **No persistence**: OTP doesn't survive server restart

## Usage Instructions

### For Staff Users
1. Click "Forgot your password?" on login page
2. Ensure "Admin" tab is selected
3. Enter your email address
4. Check email for verification code
5. Enter code and set new password

### For Students
1. Click "Forgot your password?" on login page
2. Switch to "Student" tab
3. Enter your email address (from CSV or database)
4. Check email for verification code
5. Enter code and set new password
6. Account automatically migrated to database

## Error Handling

### Common Scenarios
- **Email not found**: Clear message indicating email not in records
- **Invalid OTP**: Prompt to re-enter verification code
- **Password mismatch**: Validation error for confirmation field
- **Network errors**: Graceful fallback with retry options

### Logging
- **Server-side**: All errors logged to console
- **Client-side**: EmailJS errors captured and displayed
- **Database**: Transaction rollbacks on failures

## Testing

### Manual Testing
1. Run the application: `python run.py`
2. Navigate to login page
3. Test forgot password for both staff and students
4. Verify email delivery and OTP functionality

### Automated Testing
Use the provided test script:
```bash
python test_forgot_password.py
```

## Configuration

### Environment Variables
```env
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USERNAME=your_email@gmail.com
MAIL_PASSWORD=your_app_password
```

### EmailJS Configuration
- Update service ID and template ID in login.html
- Configure email template with verification code placeholder
- Set up proper CORS settings

## Maintenance

### Regular Tasks
1. **Monitor CSV usage**: Track which students still use CSV data
2. **Database cleanup**: Remove old session data periodically
3. **Email delivery**: Monitor EmailJS quota and delivery rates
4. **Security updates**: Keep password hashing methods current

### Troubleshooting
- **Email not sending**: Check EmailJS configuration and quotas
- **Database errors**: Verify connection and table structure
- **CSV issues**: Ensure proper file encoding and format
- **Session problems**: Check Flask session configuration

## Future Enhancements

### Potential Improvements
1. **Email templates**: HTML-formatted emails with branding
2. **Rate limiting**: Prevent OTP spam and abuse
3. **Password strength**: Advanced password requirements
4. **Audit logging**: Track all password reset attempts
5. **Multi-factor**: SMS or app-based authentication options

### Scalability Considerations
- **Database optimization**: Indexes on email fields
- **Caching**: Redis for session storage
- **Queue system**: Async email sending
- **Load balancing**: Multiple server support