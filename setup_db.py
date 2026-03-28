#!/usr/bin/env python
"""
setup_db.py — Initialize database with test users for demo.
Run: python setup_db.py
"""

import json
import os
import bcrypt

DATA_FILE = os.path.join(os.path.dirname(__file__), "data.json")


def hash_password(plain: str) -> str:
    """Return a bcrypt hash of *plain* as a UTF-8 string."""
    return bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def setup():
    """Initialize database with test users."""
    # Load existing data or create empty
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    else:
        data = {"users": [], "sessions": [], "messages": [], "feedback": []}

    # Clear and recreate with proper test users
    data["users"] = [
        {
            "user_id": "u_mentor_003",
            "name": "Spandan Guha",
            "roll_no": "M2329027",
            "email": "spandan.guhafme@kiit.ac.in",
            "password": hash_password("MENTOR123"),
            "role": "mentor",
            "contact_number": "8777601029",
            "skills": ["Computer Science", "Engineering", "Programming", "Academic Guidance"],
            "experience_years": 10,
            "rating": 4.9,
            "sessions_completed": 25,
            "availability": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"],
            "bio": "Senior faculty member at KIIT providing academic mentorship.",
            "hourly_rate": 0.0,
        },
        {
            "user_id": "u_mentor_001",
            "name": "Mentor One",
            "roll_no": "MENTOR1",
            "email": "mentor1@test.com",
            "password": hash_password("MENTOR123"),
            "role": "mentor",
            "contact_number": "9876543210",
            "skills": ["Python", "Django", "REST APIs"],
            "experience_years": 6,
            "rating": 4.8,
            "sessions_completed": 10,
            "availability": ["Monday", "Wednesday", "Friday"],
            "bio": "Backend engineer, loves teaching.",
            "hourly_rate": 55.0,
        },
        {
            "user_id": "u_mentor_002",
            "name": "Mentor Two",
            "roll_no": "MENTOR2",
            "email": "mentor2@test.com",
            "password": hash_password("MENTOR123"),
            "role": "mentor",
            "contact_number": "9123456780",
            "skills": ["JavaScript", "React", "Node.js", "Web Development"],
            "experience_years": 5,
            "rating": 4.5,
            "sessions_completed": 8,
            "availability": ["Tuesday", "Thursday", "Saturday"],
            "bio": "Full-stack developer specializing in modern web technologies.",
            "hourly_rate": 50.0,
        },
        {
            "user_id": "u_mentee_001",
            "name": "Ayush Roy",
            "roll_no": "2329027",
            "email": "ayush@test.com",
            "password": hash_password("AYUSH123"),
            "role": "mentee",
            "contact_number": "9000000001",
            "skills": ["Python"],
            "experience_years": 1,
            "rating": 4.5,
            "sessions_completed": 3,
            "availability": ["Monday", "Friday"],
            "bio": "Junior dev eager to learn.",
            "goals": ["Learn Django", "Build REST APIs"],
            "reg_no": "23356799027",
            "school": "SCSE",
            "program": "Computer Science and Communication Engineering",
            "semester": "6th Stage",
            "profile_image": "images/profiles/2329027.png",
            "assigned_mentor_id": "u_mentor_003",
        },
        {
            "user_id": "u_mentee_002",
            "name": "Student Name",
            "roll_no": "2329030",
            "email": "student@test.com",
            "password": hash_password("AYUSH123"),
            "role": "mentee",
            "contact_number": "9000000002",
            "skills": ["Python", "Web Basics"],
            "experience_years": 0,
            "rating": 0.0,
            "sessions_completed": 0,
            "availability": ["Wednesday", "Saturday"],
            "bio": "Student looking to improve programming skills.",
            "goals": ["Learn JavaScript", "Build web apps"],
            "reg_no": "23356799030",
            "school": "SCSE",
            "program": "B.Tech. (Computer Science & Engineering)",
            "semester": "2nd Stage",
        },
    ]

    # Start without active sessions; mentees will raise a concern first.
    data["sessions"] = []
    
    data["messages"] = []
    data["feedback"] = []

    # Save to file
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print("✓ Database initialized with test users.")
    print("\nTest credentials:")
    print("  Roll No: M2329027  | Password: MENTOR123")
    print("  Roll No: MENTOR1   | Password: MENTOR123")
    print("  Roll No: MENTOR2   | Password: MENTOR123")
    print("  Roll No: 2329027   | Password: AYUSH123")
    print("  Roll No: 2329030   | Password: AYUSH123")


if __name__ == "__main__":
    setup()
