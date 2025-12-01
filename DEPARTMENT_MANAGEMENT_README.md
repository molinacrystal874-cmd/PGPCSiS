# Department/Program and Section Management Feature

## Overview
This feature allows administrators to dynamically manage academic programs (departments) and their sections through the admin panel. All newly created programs and sections automatically become available in the teacher assignment forms.

## Features Added

### 1. Programs & Sections Management View
- **Location**: Admin Panel → Programs & Sections (new sidebar menu item)
- **Functionality**: 
  - View all programs and their sections in a table format
  - Add new programs (e.g., BSCS, BSIT, BPA)
  - Add new sections under existing programs (e.g., 1A, 2B, 3C)
  - Edit existing programs and sections
  - Delete programs/sections (with dependency validation)

### 2. Dynamic Teacher Form Updates
- **Teacher Assignment Forms**: Both "Add New Teacher" and "Edit Teacher" forms now dynamically load programs and sections from the database
- **Real-time Updates**: When you add/edit/delete programs or sections, the teacher forms are automatically updated
- **Backward Compatibility**: Existing teacher assignments are preserved

### 3. Database Structure
- **New Tables**: 
  - `department` - Stores program information (BSCS, BPA, etc.)
  - `section` - Stores section information linked to departments
- **Relationships**: Many-to-many relationships between teachers and departments/sections
- **Validation**: Prevents duplicate names and enforces referential integrity

## How to Use

### Adding a New Program
1. Go to Admin Panel → Programs & Sections
2. Click "Add Program" button
3. Enter program name (e.g., "BSIT", "BEED")
4. Click "Add Program"
5. The new program immediately appears in teacher assignment forms

### Adding a New Section
1. Go to Admin Panel → Programs & Sections  
2. Click "Add Section" button
3. Select the program from dropdown
4. Enter section name (e.g., "1A", "3B")
5. Click "Add Section"
6. The new section immediately appears under the selected program in teacher forms

### Editing Programs/Sections
1. In the Programs & Sections table, click "Edit" next to any program
2. Or click the edit icon next to any section
3. Update the name and save
4. Changes are reflected immediately in teacher forms

### Deleting Programs/Sections
1. Click "Delete" next to any program or section
2. System checks for dependencies (assigned teachers)
3. If no dependencies exist, deletion is allowed
4. If dependencies exist, deletion is prevented with an error message

## Technical Implementation

### Backend Routes
- `GET /api/departments` - Fetch all departments with sections
- `POST /departments` - Create new department
- `PUT /departments/<id>` - Update department
- `DELETE /departments/<id>` - Delete department
- `POST /sections` - Create new section
- `PUT /sections/<id>` - Update section  
- `DELETE /sections/<id>` - Delete section

### Database Initialization
Run `python init_departments.py` to populate the database with initial programs and sections:
- BSCS, BPA, BSCRIM, BSMA (with sections 1A-1F, 2A-2F each)
- Admin department for non-teaching staff

### Key Benefits
1. **No Code Changes Required**: Adding new programs/sections doesn't require code modifications
2. **Immediate Availability**: New items instantly appear in teacher assignment forms
3. **Data Integrity**: Prevents deletion of programs/sections with assigned teachers
4. **User-Friendly**: Simple interface for non-technical administrators
5. **Validation**: Prevents duplicate names and maintains data consistency

## Migration Notes
- Existing teacher assignments are preserved through the many-to-many relationship tables
- The system maintains backward compatibility with existing data
- No manual database changes required - everything is managed through the UI

## Future Enhancements
- Bulk import/export of programs and sections
- Program-specific settings and metadata
- Academic year/semester-based section management
- Integration with student enrollment data