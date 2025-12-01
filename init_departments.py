#!/usr/bin/env python3
"""
Initialize departments and sections in the database.
Run this script to populate the database with initial academic programs and sections.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from webapp import create_app
from webapp.models import db, Department, Section

def init_departments_and_sections():
    """Initialize departments and sections in the database."""
    app = create_app()
    
    with app.app_context():
        try:
            # Create departments if they don't exist
            departments_data = [
                'BSCS',
                'BPA', 
                'BSCRIM',
                'BSMA',
                'Admin'  # For non-teaching staff
            ]
            
            created_departments = {}
            
            for dept_name in departments_data:
                existing_dept = Department.query.filter_by(name=dept_name).first()
                if not existing_dept:
                    dept = Department(name=dept_name)
                    db.session.add(dept)
                    db.session.flush()  # Get the ID
                    created_departments[dept_name] = dept
                    print(f"Created department: {dept_name}")
                else:
                    created_departments[dept_name] = existing_dept
                    print(f"Department already exists: {dept_name}")
            
            # Create sections for academic departments
            sections_data = {
                'BSCS': ['1A', '1B', '1C', '1D', '1E', '1F', '2A', '2B', '2C', '2D', '2E', '2F'],
                'BPA': ['1A', '1B', '1C', '1D', '1E', '1F', '2A', '2B', '2C', '2D', '2E', '2F'],
                'BSCRIM': ['1A', '1B', '1C', '1D', '1E', '1F', '2A', '2B', '2C', '2D', '2E', '2F'],
                'BSMA': ['1A', '1B', '1C', '1D', '1E', '1F', '2A', '2B', '2C', '2D', '2E', '2F'],
                'Admin': ['Admin-Office']  # For non-teaching staff
            }
            
            for dept_name, section_names in sections_data.items():
                dept = created_departments[dept_name]
                for section_name in section_names:
                    existing_section = Section.query.filter_by(
                        name=section_name, 
                        department_id=dept.id
                    ).first()
                    
                    if not existing_section:
                        section = Section(name=section_name, department_id=dept.id)
                        db.session.add(section)
                        print(f"Created section: {dept_name}-{section_name}")
                    else:
                        print(f"Section already exists: {dept_name}-{section_name}")
            
            db.session.commit()
            print("\nSuccessfully initialized departments and sections!")
            
        except Exception as e:
            db.session.rollback()
            print(f"Error initializing departments and sections: {e}")
            raise

if __name__ == '__main__':
    init_departments_and_sections()