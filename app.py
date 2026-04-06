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
          <meta charset="utf-8" />
          <meta name="viewport" content="width=device-width, initial-scale=1" />
          <title>Mentor Mentee System</title>
          <style>
            :root{color-scheme:dark}
            body{margin:0;min-height:100vh;font-family:Segoe UI,system-ui,Arial;background:#020617;color:#E5EEF9;display:flex;align-items:center;justify-content:center;padding:20px}
            main{width:min(920px,100%);background:rgba(8,17,32,0.86);padding:28px;border-radius:14px;border:1px solid rgba(148,163,184,0.06);box-shadow:0 20px 60px rgba(2,6,23,0.5)}
            h1{margin:0 0 6px;font-size:28px}
            .muted{color:#9fb2c9;margin-bottom:12px}
            .cols{display:grid;grid-template-columns:320px 1fr;gap:18px}
            .card{background:rgba(15,23,42,0.6);padding:14px;border-radius:10px;border:1px solid rgba(148,163,184,0.04)}
            label{display:block;font-weight:600;margin:8px 0 6px}
            input,select{width:100%;padding:8px;border-radius:6px;border:1px solid #203046;background:#071926;color:#EAF6FF}
            button{margin-top:10px;padding:8px 12px;border-radius:8px;border:none;background:#22d3ee;color:#042027;font-weight:700;cursor:pointer}
            #mentors div{padding:6px 8px;border-radius:6px;margin-bottom:6px;background:rgba(2,6,23,0.4);cursor:pointer}
            #status,#session_status{margin-top:8px;color:#BAE6FD}
          </style>
        </head>
        <body>
          <main>
            <h1>Mentor Mentee System — Demo UI</h1>
            <div class="muted">Small client to exercise the API endpoints: login, mentors, sessions.</div>
            <div class="cols">
              <div>
                <div class="card">
                  <strong>Login</strong>
                  <label for="roll">Roll No.</label>
                  <input id="roll" placeholder="e.g. 20BCS123" />
                  <label for="pass">Password</label>
                  <input id="pass" type="password" placeholder="password" />
                  <button onclick="login()">Log In</button>
                  <div id="status"></div>
                </div>

                <div class="card" style="margin-top:12px">
                  <strong>Mentors</strong>
                  <div id="mentors" style="margin-top:8px"></div>
                </div>
              </div>

              <div>
                <div class="card">
                  <strong>Create Session</strong>
                  <label for="mentor_id">Mentor ID</label>
                  <input id="mentor_id" placeholder="Select mentor or paste ID" />
                  <label for="mentee_id">Mentee ID</label>
                  <input id="mentee_id" placeholder="Your user_id (optional if logged in)" />
                  <label for="date">Date</label>
                  <input id="date" type="date" />
                  <label for="time">Time</label>
                  <input id="time" type="time" />
                  <button onclick="createSession()">Create Session</button>
                  <div id="session_status"></div>
                </div>

                <div class="card" style="margin-top:12px">
                  <strong>Quick Links</strong>
                  <div style="margin-top:8px"><a href="/health">/health</a> • <a href="/demo">/demo</a> • <a href="/?format=json">API metadata</a></div>
                </div>

                <div class="card" style="margin-top:12px">
                  <strong>My Sessions</strong>
                  <div id="sessions" style="margin-top:8px"></div>
                  <button onclick="loadSessions()" style="margin-top:8px">Refresh sessions</button>
                </div>
              </div>
            </div>

            <script>
              async function login(){
                const roll = document.getElementById('roll').value.trim();
                const pass = document.getElementById('pass').value;
                if(!roll||!pass){document.getElementById('status').innerText='Enter roll and password';return}
                const res = await fetch('/login',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({roll_no:roll,password:pass})});
                const data = await res.json().catch(()=>({ok:false,error:'Invalid response'}));
                if(res.ok && data.ok){
                  document.getElementById('status').innerText = 'Logged in: '+(data.user.name||data.user.roll_no);
                  window.currentUser = data.user;
                  document.getElementById('mentee_id').value = data.user.user_id || '';
                } else {
                  document.getElementById('status').innerText = data.error || 'Login failed';
                }
                loadMentors();
              }

              async function loadMentors(){
                const res = await fetch('/mentors');
                const data = await res.json().catch(()=>({ok:false}));
                const container = document.getElementById('mentors');
                container.innerHTML='';
                if(data.ok && data.mentors && data.mentors.length){
                  data.mentors.forEach(m=>{
                    const el = document.createElement('div');
                    el.textContent = (m.name||m.roll_no||'(no name)') + ' — ' + (m.email||'');
                    el.dataset.id = m.user_id;
                    el.onclick = ()=> document.getElementById('mentor_id').value = m.user_id;
                    container.appendChild(el);
                  })
                } else {
                  container.textContent = 'No mentors available.';
                }
              }

              async function createSession(){
                const mentor_id = document.getElementById('mentor_id').value.trim();
                const mentee_id = (window.currentUser && window.currentUser.user_id) || document.getElementById('mentee_id').value.trim();
                const date = document.getElementById('date').value;
                const time = document.getElementById('time').value;
                if(!mentor_id||!mentee_id||!date||!time){document.getElementById('session_status').innerText='Please fill all fields';return}
                const res = await fetch('/sessions',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({mentor_id,mentee_id,date,time})});
                const data = await res.json().catch(()=>({ok:false,error:'Invalid response'}));
                if(res.ok && data.ok){
                  document.getElementById('session_status').innerText = 'Created session: '+(data.session.session_id||'');
                  loadSessions();
                } else {
                  document.getElementById('session_status').innerText = data.error || 'Failed to create session';
                }
              }

                async function loadSessions(){
                  const userId = (window.currentUser && window.currentUser.user_id) || '';
                  const url = userId ? `/sessions?user_id=${encodeURIComponent(userId)}` : '/sessions';
                  try{
                    const res = await fetch(url);
                    const data = await res.json().catch(()=>({ok:false}));
                    const container = document.getElementById('sessions');
                    container.innerHTML = '';
                    if(data.ok && Array.isArray(data.sessions) && data.sessions.length){
                      data.sessions.forEach(s=>{
                        const el = document.createElement('div');
                        el.textContent = `${s.session_id || ''} — ${s.topic || s.concern || ''} — ${s.date || ''} ${s.time || ''} (${s.status || ''})`;
                        container.appendChild(el);
                      });
                    } else {
                      container.textContent = 'No sessions found.';
                    }
                  } catch(e){
                    document.getElementById('sessions').innerText = 'Error loading sessions';
                  }
                }

                window.addEventListener('load', ()=>{ loadMentors(); loadSessions(); });
            </script>
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


@app.get("/users")
def http_list_users():
    users = database.get_all_users()
    safe = [{k: v for k, v in u.items() if k != "password"} for u in users]
    return jsonify({"ok": True, "users": safe})


@app.post("/users")
def http_create_user():
    data = request.get_json(silent=True) or {}
    required = ("name", "roll_no", "email", "password")
    if not all(k in data for k in required):
        return jsonify({"ok": False, "error": "missing fields"}), 400
    pwd = data.pop("password")
    hashed = auth.hash_password(pwd)
    user = {
        "name": data.get("name"),
        "roll_no": data.get("roll_no"),
        "email": data.get("email"),
        "role": data.get("role", "mentee"),
        "password": hashed,
    }
    created = database.create_user(user)
    safe = {k: v for k, v in created.items() if k != "password"}
    return jsonify({"ok": True, "user": safe}), 201


@app.get("/mentors")
def http_list_mentors():
    mentors = database.get_users_by_role("mentor")
    safe = [{k: v for k, v in u.items() if k != "password"} for u in mentors]
    return jsonify({"ok": True, "mentors": safe})


@app.get("/sessions")
def http_list_sessions():
    user_id = request.args.get("user_id")
    if user_id:
        sessions = database.get_sessions_for_user(user_id)
    else:
        sessions = database.get_all_sessions()
    return jsonify({"ok": True, "sessions": sessions})


@app.get("/sessions/<session_id>")
def http_get_session(session_id):
    s = database.get_session_by_id(session_id)
    if not s:
        return jsonify({"ok": False, "error": "not found"}), 404
    return jsonify({"ok": True, "session": s})


@app.put("/sessions/<session_id>")
def http_update_session(session_id):
    data = request.get_json(silent=True) or {}
    updated = database.update_session(session_id, data)
    if not updated:
        return jsonify({"ok": False, "error": "not found"}), 404
    return jsonify({"ok": True, "session": updated})


@app.post("/sessions")
def http_create_session():
    data = request.get_json(silent=True) or {}
    required = ("mentor_id", "mentee_id", "date", "time")
    if not all(k in data for k in required):
        return jsonify({"ok": False, "error": "missing fields"}), 400
    session = database.create_session(data)
    return jsonify({"ok": True, "session": session}), 201


@app.get("/messages")
def http_get_messages():
    user_a = request.args.get("user_a")
    user_b = request.args.get("user_b")
    session_id = request.args.get("session_id")
    if user_a and user_b:
        conv = database.get_conversation(user_a, user_b, session_id)
        return jsonify({"ok": True, "messages": conv})
    return jsonify({"ok": True, "messages": database.get_all_messages()})


@app.post("/messages")
def http_create_message():
    data = request.get_json(silent=True) or {}
    required = ("sender_id", "receiver_id", "text")
    if not all(k in data for k in required):
        return jsonify({"ok": False, "error": "missing fields"}), 400
    message = {
        "sender_id": data["sender_id"],
        "receiver_id": data["receiver_id"],
        "text": data["text"],
        "session_id": data.get("session_id"),
    }
    created = database.create_message(message)
    return jsonify({"ok": True, "message": created}), 201


@app.get("/feedback")
def http_list_feedback():
    user_id = request.args.get("user_id")
    if user_id:
        fb_list = database.get_feedback_for_user(user_id)
    else:
        fb_list = database.get_all_feedback()
    return jsonify({"ok": True, "feedback": fb_list})


@app.post("/feedback")
def http_create_feedback():
    data = request.get_json(silent=True) or {}
    required = ("reviewee_id", "reviewer_id", "rating")
    if not all(k in data for k in required):
        return jsonify({"ok": False, "error": "missing fields"}), 400
    feedback = {
        "reviewee_id": data["reviewee_id"],
        "reviewer_id": data["reviewer_id"],
        "rating": data["rating"],
        "comment": data.get("comment", ""),
        "session_id": data.get("session_id"),
    }
    created = database.create_feedback(feedback)
    return jsonify({"ok": True, "feedback": created}), 201
