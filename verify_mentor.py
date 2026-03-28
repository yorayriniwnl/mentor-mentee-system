#!/usr/bin/env python
"""Verify mentor assignment for 2329027."""

import database as db

ayush = db.get_user_by_roll_no("2329027")
if not ayush:
    raise SystemExit("Student 2329027 not found.")

mentor = db.get_assigned_mentor(ayush["user_id"])

print(f"Student: {ayush['name']} ({ayush['roll_no']})")
print(f"Assigned Mentor ID: {ayush.get('assigned_mentor_id', 'Not set')}")

if not mentor:
    raise SystemExit("No mentor is currently assigned.")

print("\nMentor Information:")
print(f"  Name: {mentor['name']}")
print(f"  Contact Number: {mentor['contact_number']}")
print(f"  E-mail ID: {mentor['email']}")
