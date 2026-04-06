# Mentor Mentee System

Lightweight Mentor/Mentee system — Flask API layer + a Tkinter desktop GUI.

This repository contains:

- `gui.py` — Tkinter desktop GUI (desktop-only, not deployable to serverless hosts).
- `app.py` — Flask app used for the web API and a small demo UI.
- `api/index.py` — Vercel function entry that imports `app`.
- `vercel.json` — Vercel configuration (routes + python build).
- `data.json` — JSON-backed datastore used by `database.py`.

## Quick start (local)

1. Create and activate a virtual environment (PowerShell):

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Or on macOS / Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

2. Install dependencies:

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

3. Run the Flask app for local testing (port 3000):

```bash
python -m flask --app app run --port 3000
```

Then open http://127.0.0.1:3000/ in your browser.

Notes:
- The desktop `gui.py` is meant to be run locally with `python main.py` and will not work on Vercel.
- The demo endpoint `/demo` runs against an isolated copy of `data.json` so the repo file is not mutated.

## Tests

Run the pytest smoke tests added under `tests/`:

```bash
pip install pytest
pytest -q
```

## API Endpoints (examples)

- `GET /` — API metadata and minimal UI.
- `GET /health` — health check.
- `GET /demo` — CLI demo output (uses isolated DB copy).
- `POST /login` — login with JSON `{ "roll_no": "...", "password": "..." }`.
- `GET /mentors` — list mentors.
- `GET /sessions` — list sessions (optional `?user_id=` filter).
- `POST /sessions` — create session: `{ "mentor_id": "...", "mentee_id": "...", "date": "YYYY-MM-DD", "time": "HH:MM" }`.

Examples (curl):

```bash
curl http://127.0.0.1:3000/health

curl -X POST http://127.0.0.1:3000/login -H 'Content-Type: application/json' \
  -d '{"roll_no":"20BCS123","password":"Secret123!"}'

curl http://127.0.0.1:3000/mentors

curl -X POST http://127.0.0.1:3000/sessions -H 'Content-Type: application/json' \
  -d '{"mentor_id":"u_mentor_001","mentee_id":"u_mentee_001","date":"2026-04-07","time":"10:00"}'
```

## Deploy to Vercel

This repo is already configured for Vercel via `vercel.json` — the serverless handler is `api/index.py` which imports the Flask `app` from `app.py`.

Recommended flow:

1. Push to GitHub (already done).
2. Create a new Project in Vercel and import this GitHub repository.
3. Vercel will use the `vercel.json` build configuration to expose the Flask API.

Alternatively, deploy with the Vercel CLI:

```bash
npm i -g vercel
vercel login
vercel --prod
```

If you want automatic deploys from GitHub, enable the GitHub integration in Vercel — no extra repo changes required.

## Security & Notes

- Passwords are hashed with `bcrypt` and never stored in plain text.
- `data.json` is the source-of-truth for the demo; avoid mutating it in serverless demo runs (the demo endpoint uses a temp copy).
- The current demo UI is intentionally minimal; for production you should add auth tokens and rate-limiting.

If you want, I can add a GitHub Action to automatically deploy to Vercel when you provide a `VERCEL_TOKEN` secret.
