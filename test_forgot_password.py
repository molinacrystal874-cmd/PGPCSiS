#!/usr/bin/env python3
"""
Test script for forgot password functionality
"""

import requests
import json

def test_forgot_password():
    base_url = "http://localhost:5000"
    
    print("Testing Forgot Password Functionality")
    print("=" * 50)
    
    # Test 1: Staff user forgot password
    print("\n1. Testing staff user forgot password...")
    staff_data = {
        "email": "admin@pgpc.edu",
        "user_type": "staff"
    }
    
    try:
        response = requests.post(f"{base_url}/forgot-password", 
                               json=staff_data,
                               headers={'Content-Type': 'application/json'})
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.json()}")
    except Exception as e:
        print(f"Error: {e}")
    
    # Test 2: Student user forgot password (CSV)
    print("\n2. Testing CSV student forgot password...")
    student_data = {
        "email": "crystalyn079@gmail.com",
        "user_type": "student"
    }
    
    try:
        response = requests.post(f"{base_url}/forgot-password", 
                               json=student_data,
                               headers={'Content-Type': 'application/json'})
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.json()}")
    except Exception as e:
        print(f"Error: {e}")
    
    # Test 3: Invalid email
    print("\n3. Testing invalid email...")
    invalid_data = {
        "email": "nonexistent@example.com",
        "user_type": "student"
    }
    
    try:
        response = requests.post(f"{base_url}/forgot-password", 
                               json=invalid_data,
                               headers={'Content-Type': 'application/json'})
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.json()}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_forgot_password()