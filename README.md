# Mentor Mentee System

A lightweight mentor/mentee platform with a Flask API layer, a Tkinter desktop GUI, and a Vercel-ready serverless entrypoint.

## Screenshot / GIF

![Mentor Mentee System screenshot](./assets/mentor-mentee-system-screenshot.gif)

[Live demo](https://mentor-mentee-system.vercel.app)

## Tech Stack

- Python
- Flask
- Tkinter
- SQLite / JSON datastore
- Vercel

## Setup Instructions

1. Create and activate a virtual environment.
2. Install dependencies with `pip install -r requirements.txt`.
3. Run the Flask app with `python -m flask --app app run --port 3000`.
4. Open `http://127.0.0.1:3000/` in your browser.
5. Optional: run the desktop GUI locally with `python main.py`.

## Notes

The desktop GUI is local-only; the web API is the part meant for deployment.
