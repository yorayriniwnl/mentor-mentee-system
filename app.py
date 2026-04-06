from __future__ import annotations

import io
import shutil
import tempfile
from contextlib import contextmanager, redirect_stdout
from pathlib import Path

from flask import Flask, jsonify, request
import auth
import database

app = Flask(__name__)


@contextmanager
def _isolated_demo_database():
    """
    Run the CLI demo against a temporary copy of data.json.

    Vercel functions can read bundled files but should not mutate them directly,
    so the demo uses an isolated writable copy instead of the repo file.
    """
    import database

    source = Path(__file__).with_name("data.json")
    temp_dir = Path(tempfile.mkdtemp(prefix="mentor-demo-"))
    temp_file = temp_dir / "data.json"
    shutil.copy2(source, temp_file)

    original_data_file = database.DATA_FILE
    database.DATA_FILE = str(temp_file)
    try:
        yield
    finally:
        database.DATA_FILE = original_data_file
        shutil.rmtree(temp_dir, ignore_errors=True)


@app.get("/")
def root():
    payload = {
        "name": "Mentor Mentee System",
        "deployment": "vercel",
        "mode": "api",
        "note": "Desktop Tkinter GUI is not available on Vercel. Use local run for GUI.",
        "endpoints": ["/", "/health", "/demo"],
    }

    wants_json = request.args.get("format", "").lower() == "json"
    accepts_html = request.accept_mimetypes.accept_html
    prefers_html = (
        request.accept_mimetypes["text/html"]
        >= request.accept_mimetypes["application/json"]
    )

    if not wants_json and accepts_html and prefers_html:
        return """
        <!doctype html>
        <html lang="en">
        <head>
          <meta charset="utf-8">
          <meta name="viewport" content="width=device-width, initial-scale=1">
          <title>Mentor Mentee System</title>
          <style>
            :root {
              color-scheme: dark;
              --bg: #07111f;
              --panel: rgba(8, 17, 32, 0.82);
              --line: rgba(148, 163, 184, 0.18);
              --text: #e5eefb;
              --muted: #9fb2c9;
              --accent: #22d3ee;
              --accent-2: #38bdf8;
            }
            * { box-sizing: border-box; }
            body {
              margin: 0;
              min-height: 100vh;
              font-family: "Segoe UI", sans-serif;
              color: var(--text);
              background:
                radial-gradient(circle at top, rgba(56, 189, 248, 0.28), transparent 38%),
                linear-gradient(160deg, #020617 0%, var(--bg) 100%);
              display: grid;
              place-items: center;
              padding: 24px;
            }
            main {
              width: min(760px, 100%);
              padding: 32px;
              border: 1px solid var(--line);
              border-radius: 24px;
              background: var(--panel);
              backdrop-filter: blur(12px);
              box-shadow: 0 24px 70px rgba(2, 6, 23, 0.45);
            }
            .eyebrow {
              color: var(--accent);
              font-size: 0.84rem;
              font-weight: 700;
              letter-spacing: 0.12em;
              text-transform: uppercase;
            }
            h1 {
              margin: 12px 0;
              font-size: clamp(2rem, 4vw, 3.2rem);
              line-height: 1.05;
            }
            p {
              color: var(--muted);
              font-size: 1rem;
              line-height: 1.7;
              margin: 0 0 16px;
            }
            .grid {
              display: grid;
              gap: 16px;
              grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
              margin-top: 24px;
            }
            .card {
              border: 1px solid var(--line);
              border-radius: 18px;
              padding: 18px;
              background: rgba(15, 23, 42, 0.66);
            }
            .card strong {
              display: block;
              margin-bottom: 8px;
              color: var(--text);
            }
            a {
              color: var(--accent-2);
              text-decoration: none;
            }
            a:hover { text-decoration: underline; }
            code {
              color: var(--text);
              background: rgba(15, 23, 42, 0.9);
              border: 1px solid var(--line);
              border-radius: 10px;
              padding: 2px 8px;
            }
          </style>
        </head>
        <body>
          <main>
            <div class="eyebrow">Vercel Deployment</div>
            <h1>Mentor Mentee System</h1>
            <p>
              This deployment is running the web-safe serverless layer of the project.
              The full Tkinter desktop GUI from <code>gui.py</code> cannot run inside a browser or on Vercel.
            </p>
            <p>
              You can still use the live diagnostics endpoints below, or run the desktop app locally with
              <code>python main.py</code>.
            </p>
            <div class="grid">
              <div class="card">
                <strong>Health Check</strong>
                <a href="/health">/health</a>
              </div>
              <div class="card">
                <strong>Demo Output</strong>
                <a href="/demo">/demo</a>
              </div>
              <div class="card">
                <strong>API Metadata</strong>
                <a href="/?format=json">/?format=json</a>
              </div>
            </div>
          </main>
        </body>
        </html>
        """

    return jsonify(payload)


@app.get("/health")
def health():
    return jsonify({"status": "ok"})


@app.get("/demo")
def demo():
    from main import run_demo

    buffer = io.StringIO()
    with _isolated_demo_database(), redirect_stdout(buffer):
        run_demo()

    return jsonify({"output": buffer.getvalue()})


  # ─────────────────────── Additional API Endpoints ───────────────────────

  @app.post("/login")
  def http_login():
    data = request.get_json(silent=True) or {}
    roll_no = data.get("roll_no") or data.get("roll") or data.get("username")
    password = data.get("password", "")
    if not roll_no or not password:
      return jsonify({"ok": False, "error": "missing credentials"}), 400
    ok, user = auth.login(roll_no, password)
    if not ok:
      return jsonify({"ok": False, "error": "invalid credentials"}), 401
    return jsonify({"ok": True, "user": user})


  @app.get("/users/<user_id>")
  def http_get_user(user_id):
    profile = auth.get_profile(user_id)
    if not profile:
      return jsonify({"ok": False, "error": "not found"}), 404
    return jsonify({"ok": True, "user": profile})


  @app.get("/mentors")
  def http_list_mentors():
    mentors = database.get_users_by_role("mentor")
    safe = [{k: v for k, v in u.items() if k != "password"} for u in mentors]
    return jsonify({"ok": True, "mentors": safe})


  @app.post("/sessions")
  def http_create_session():
    data = request.get_json(silent=True) or {}
    required = ("mentor_id", "mentee_id", "date", "time")
    if not all(k in data for k in required):
      return jsonify({"ok": False, "error": "missing fields"}), 400
    session = database.create_session(data)
    return jsonify({"ok": True, "session": session}), 201
