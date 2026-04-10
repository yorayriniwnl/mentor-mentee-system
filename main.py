"""
main.py - Entry point for the Menor Mentee Portal.

Usage:
    python main.py           # Launch the Tkinter GUI
    python main.py --demo    # Run a CLI demonstration of all modules
"""

import sys


def run_gui():
    """Launch the Tkinter application."""
    try:
        from gui import MentorApp
    except ModuleNotFoundError as e:
        missing = e.name or "a required package"
        package_hints = {
            "jwt": "PyJWT",
            "PIL": "Pillow",
        }
        install_target = package_hints.get(missing, missing)
        print(f"GUI unavailable: missing dependency '{missing}'")
        print(f"Install it with:  python -m pip install {install_target}")
        print("Or install all project dependencies with:  python -m pip install -r requirements.txt")
        sys.exit(1)
    except ImportError as e:
        print(f"GUI unavailable: {e}")
        print("Install project dependencies with:  python -m pip install -r requirements.txt")
        sys.exit(1)

    app = MentorApp()
    app.mainloop()


def run_demo():
    """
    CLI walkthrough: login -> matching -> session request -> messaging -> analytics.
    Prints results to stdout so you can verify everything works without opening the GUI.
    """
    import analytics
    import auth
    import booking
    import matching
    import messaging
    from database import get_all_sessions

    sep = "-" * 55

    print(sep)
    print("  MENOR MENTEE PORTAL - CLI DEMO")
    print(sep)

    print("\n[1] Logging in demo users ...")
    _, mentor_user = auth.login("M2329027", "MENTOR123")
    mentor_id = mentor_user["user_id"]
    print(f"  [OK] Mentor logged in -> ID: {mentor_id}")

    _, mentee_user = auth.login("2329027", "AYUSH123")
    mentee_id = mentee_user["user_id"]
    print(f"  [OK] Mentee logged in -> ID: {mentee_id}")

    print("\n[2] Assigned mentor ...")
    print(f"  [OK] Assigned mentor -> {mentor_user['name']}")

    print("\n[3] Finding matches ...")
    matches = matching.find_matches(mentee_id, top_n=3)
    for mentor, score in matches:
        print(f"  -> {mentor['name']:20s}  score={score:.1f}")

    print("\n[4] Requesting a session ...")
    ok, msg = booking.book_session(
        mentee_id=mentee_id,
        concern="Need guidance on Django REST Framework and project planning.",
    )
    print(f"  {'[OK]' if ok else '[X]'} {msg}")

    sessions = [
        s for s in get_all_sessions()
        if s["mentor_id"] == mentor_id and s["mentee_id"] == mentee_id
    ]
    session_id = sessions[-1]["session_id"] if sessions else None

    if session_id:
        print("\n[5] Request status ...")
        print(f"  Current status: {sessions[-1]['status'].upper()}")

    print("\n[6] Sending messages ...")
    ok, info, _ = messaging.send_message(mentee_id, mentor_id, "Thanks for the session!")
    print(f"  {'[OK]' if ok else '[X]'} {info}")

    print("\n[7] Feedback ...")
    print("  Skipped: feedback is available after a completed session.")

    print("\n[8] Analytics ...")
    summary = analytics.platform_summary()
    print(f"  Mentors       : {summary['total_mentors']}")
    print(f"  Mentees       : {summary['total_mentees']}")
    print(f"  Sessions      : {summary['sessions']['total']}")
    print(f"  Avg Rating    : {summary['avg_platform_rating']}")
    print(f"  Completion %  : {summary['sessions']['completion_rate']}%")

    print("\n[TOP 3 MENTORS]")
    for mentor in analytics.top_mentors(n=3):
        print(
            f"  #{mentor['rank']} {mentor['name']:22s} "
            f"*{mentor['rating']:.1f}  score={mentor['composite_score']:.2f}"
        )

    print(f"\n{sep}")
    print("  Demo complete. Run `python main.py` to open the GUI.")
    print(sep)


if __name__ == "__main__":
    if "--demo" in sys.argv:
        run_demo()
    else:
        run_gui()
