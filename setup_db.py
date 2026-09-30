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
            "name": "Mentor Three",
            "roll_no": "MENTOR3",
            "email": "mentor3@example.test",
            "password": hash_password("MENTOR123"),
            "role": "mentor",
            "contact_number": "5550100003",
            "skills": ["Computer Science", "Engineering", "Programming", "Academic Guidance"],
            "experience_years": 10,
            "rating": 4.9,
            "sessions_completed": 25,
            "availability": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"],
            "bio": "Synthetic mentor profile for local development and tests.",
            "hourly_rate": 0.0,
        },
        {
            "user_id": "u_mentor_001",
            "name": "Mentor One",
            "roll_no": "MENTOR1",
            "email": "mentor1@example.test",
            "password": hash_password("MENTOR123"),
            "role": "mentor",
            "contact_number": "5550100001",
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
            "email": "mentor2@example.test",
            "password": hash_password("MENTOR123"),
            "role": "mentor",
            "contact_number": "5550100002",
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
            "name": "Demo Student One",
            "roll_no": "STUDENT1",
            "email": "student1@example.test",
            "password": hash_password("STUDENT123"),
            "role": "mentee",
            "contact_number": "5550200001",
            "skills": ["Python"],
            "experience_years": 1,
            "rating": 4.5,
            "sessions_completed": 3,
            "availability": ["Monday", "Friday"],
            "bio": "Junior dev eager to learn.",
            "goals": ["Learn Django", "Build REST APIs"],
            "reg_no": "DEMO-REG-001",
            "school": "SCSE",
            "program": "Demo Engineering Program",
            "semester": "6th Stage",
            "profile_image": "images/profiles/STUDENT1.png",
            "assigned_mentor_id": "u_mentor_003",
        },
        {
            "user_id": "u_mentee_002",
            "name": "Demo Student Two",
            "roll_no": "STUDENT2",
            "email": "student2@example.test",
            "password": hash_password("STUDENT123"),
            "role": "mentee",
            "contact_number": "5550200002",
            "skills": ["Python", "Web Basics"],
            "experience_years": 0,
            "rating": 0.0,
            "sessions_completed": 0,
            "availability": ["Wednesday", "Saturday"],
            "bio": "Student looking to improve programming skills.",
            "goals": ["Learn JavaScript", "Build web apps"],
            "reg_no": "DEMO-REG-002",
            "school": "SCSE",
            "program": "Demo Engineering Program",
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
    print("  Roll No: MENTOR3  | Password: MENTOR123")
    print("  Roll No: MENTOR1   | Password: MENTOR123")
    print("  Roll No: MENTOR2   | Password: MENTOR123")
    print("  Roll No: STUDENT1  | Password: STUDENT123")
    print("  Roll No: STUDENT2  | Password: STUDENT123")


if __name__ == "__main__":
    setup()