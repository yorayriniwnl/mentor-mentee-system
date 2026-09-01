from __future__ import annotations

import io
import shutil
import tempfile
from contextlib import contextmanager, redirect_stdout
from pathlib import Path

from flask import Flask, jsonify, request, g
from functools import wraps
import logging
import auth
import database
import os
import datetime
import jwt

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
        "note": "The browser surface is a demo client for the API. Use local run for the Tkinter GUI.",
        "surfaces": {
            "api_contract": "VERIFIED",
            "browser_client": "DEMO",
            "matching_engine": "EXPERIMENTAL",
            "tkinter_gui": "EXPERIMENTAL",
        },
        "endpoints": [
            "/health",
            "/demo",
            "/token",
            "/me",
            "/users",
            "/mentors",
            "/sessions",
            "/messages",
            "/feedback",
        ],
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
          <meta name="theme-color" content="#000000" />
          <link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'%3E%3Crect width='32' height='32' fill='%23000000'/%3E%3Cpath d='M6 6h20v20H6z' fill='%23e84b4b'/%3E%3C/svg%3E" />
          <title>YOR // Mentor Mentee System</title>
          <style>
            :root{color-scheme:dark;--yor-void:#000;--yor-graphite:#050505;--yor-crimson:#e84b4b;--yor-deep:#671515;--yor-signal:#ff8a7f;--yor-warm:#f5eaea;--yor-muted:#c4c4c4;--yor-line:rgba(245,234,234,.16)}
            *{box-sizing:border-box}
            body{margin:0;min-height:100vh;font-family:Inter,Segoe UI,system-ui,Arial,sans-serif;background:var(--yor-void);color:var(--yor-warm);display:flex;align-items:center;justify-content:center;padding:clamp(16px,4vw,48px);background-image:linear-gradient(rgba(232,75,75,.07) 1px,transparent 1px),linear-gradient(90deg,rgba(232,75,75,.07) 1px,transparent 1px),radial-gradient(circle at 85% 0%,rgba(103,21,21,.34),transparent 34rem);background-size:32px 32px,32px 32px,100% 100%}
            main{width:min(1080px,100%);background:linear-gradient(145deg,rgba(5,5,5,.97),rgba(20,4,4,.95));padding:clamp(20px,4vw,42px);border:1px solid var(--yor-line);box-shadow:0 28px 100px rgba(103,21,21,.2);position:relative;overflow:hidden}
            main:before{content:"";position:absolute;inset:0;pointer-events:none;opacity:.06;background-image:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='120' height='120' viewBox='0 0 120 120'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='.8' numOctaves='3' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)' opacity='.7'/%3E%3C/svg%3E")}
            main>*{position:relative}
            header{display:flex;align-items:flex-start;justify-content:space-between;gap:24px;margin-bottom:28px}
            .eyebrow,.kicker{font:600 11px/1.2 ui-monospace,SFMono-Regular,Consolas,monospace;letter-spacing:.18em;text-transform:uppercase;color:var(--yor-signal)}
            h1{margin:8px 0 10px;font-family:Georgia,serif;font-size:clamp(30px,5vw,54px);font-weight:500;letter-spacing:-.04em;line-height:1}
            .lede{max-width:620px;color:var(--yor-muted);line-height:1.65;margin:0}
            .status-chip{border:1px solid rgba(232,75,75,.6);color:var(--yor-warm);padding:9px 11px;font:600 10px/1 ui-monospace,SFMono-Regular,Consolas,monospace;letter-spacing:.12em;white-space:nowrap}
            .cols{display:grid;grid-template-columns:minmax(260px, .78fr) minmax(0, 1.22fr);gap:18px}
            .stack{display:grid;gap:18px;align-content:start}
            .card{background:rgba(5,5,5,.72);padding:18px;border:1px solid var(--yor-line);min-width:0}
            .card-head{display:flex;align-items:baseline;justify-content:space-between;gap:12px;margin-bottom:14px}
            .card-title{font-family:Georgia,serif;font-size:22px}
            .card-note{color:#8e8e8e;font:10px ui-monospace,SFMono-Regular,Consolas,monospace;letter-spacing:.08em;text-transform:uppercase}
            label{display:block;font:600 11px/1.2 ui-monospace,SFMono-Regular,Consolas,monospace;letter-spacing:.1em;text-transform:uppercase;color:var(--yor-muted);margin:14px 0 7px}
            input,select{display:block;width:100%;padding:11px 12px;border-radius:0;border:1px solid rgba(245,234,234,.2);background:#080808;color:var(--yor-warm);font:inherit;min-height:42px}
            input:focus,select:focus{outline:2px solid var(--yor-signal);outline-offset:2px;border-color:var(--yor-signal)}
            button{margin-top:14px;padding:11px 14px;border:1px solid var(--yor-crimson);border-radius:0;background:var(--yor-crimson);color:#000;font-weight:800;letter-spacing:.04em;cursor:pointer;transition:background .2s,color .2s,transform .2s}
            button:hover{background:var(--yor-signal)}
            button:focus-visible{outline:2px solid var(--yor-warm);outline-offset:3px}
            button:active{transform:translateY(1px)}
            .secondary{background:transparent;color:var(--yor-warm);border-color:rgba(245,234,234,.3)}
            .secondary:hover{background:var(--yor-deep);border-color:var(--yor-crimson)}
            .list{display:grid;gap:8px}
            #mentors div{padding:11px 12px;border-left:2px solid var(--yor-deep);background:rgba(103,21,21,.12);cursor:pointer;color:var(--yor-muted);transition:border-color .2s,background .2s,color .2s}
            #mentors div:hover,#mentors div:focus-visible{border-color:var(--yor-signal);background:rgba(103,21,21,.3);color:var(--yor-warm);outline:none}
            #status,#session_status{margin-top:12px;color:var(--yor-signal);font:12px/1.5 ui-monospace,SFMono-Regular,Consolas,monospace;min-height:18px}
            #sessions{display:grid;gap:8px}
            .session-row{display:flex;justify-content:space-between;align-items:center;gap:12px;padding:11px 12px;border:1px solid rgba(245,234,234,.1);background:rgba(245,234,234,.03);color:var(--yor-muted);font-size:13px}
            .session-copy{min-width:0;overflow-wrap:anywhere}
            .session-row button{flex:0 0 auto;margin:0;padding:7px 10px;background:transparent;color:var(--yor-signal);border-color:var(--yor-deep);font-size:11px}
            .session-row button:hover{background:var(--yor-deep);color:var(--yor-warm)}
            .links{display:flex;flex-wrap:wrap;gap:8px 16px;margin-top:10px}
            a{color:var(--yor-signal);text-underline-offset:3px}
            a:hover{color:var(--yor-warm)}
            .footer-line{margin-top:24px;padding-top:14px;border-top:1px solid rgba(245,234,234,.1);display:flex;justify-content:space-between;gap:12px;color:#8e8e8e;font:10px ui-monospace,SFMono-Regular,Consolas,monospace;letter-spacing:.08em;text-transform:uppercase}
            @media (max-width:760px){body{align-items:flex-start;padding:12px}header{display:block}.status-chip{display:inline-block;margin-top:18px}.cols{grid-template-columns:1fr}.card{padding:16px}.footer-line{display:block}.footer-line span+span{display:block;margin-top:8px}}
            @media (prefers-reduced-motion:reduce){*,*:before,*:after{scroll-behavior:auto!important;transition:none!important}}
          </style>
        </head>
        <body>
          <main>
            <header>
              <div>
                <div class="eyebrow">YOR // connection infrastructure</div>
                <h1>Mentor Mentee System</h1>
                <p class="lede">A small, auditable client for testing identity, mentor discovery, and session workflow across the shared API.</p>
              </div>
              <div class="status-chip">BROWSER / DEMO</div>
            </header>
            <div class="cols">
              <div class="stack">
                <div class="card">
                  <div class="card-head"><span class="card-title">Access</span><span class="card-note">JWT boundary</span></div>
                  <label for="roll">Roll No.</label>
                  <input id="roll" autocomplete="username" placeholder="e.g. 20BCS123" />
                  <label for="pass">Password</label>
                  <input id="pass" type="password" autocomplete="current-password" placeholder="password" />
                  <button type="button" onclick="login()">Authenticate</button>
                  <div id="status" role="status" aria-live="polite"></div>
                </div>

                <div class="card">
                  <div class="card-head"><span class="card-title">Mentor index</span><span class="card-note">Select a target</span></div>
                  <div id="mentors" class="list" aria-live="polite"></div>
                </div>
              </div>

              <div class="stack">
                <div class="card">
                  <div class="card-head"><span class="card-title">Request a session</span><span class="card-note">Protected write</span></div>
                  <label for="mentor_id">Mentor ID</label>
                  <input id="mentor_id" placeholder="Select mentor or paste ID" />
                  <label for="mentee_id">Mentee ID</label>
                  <input id="mentee_id" placeholder="Filled after authentication" />
                  <label for="date">Date</label>
                  <input id="date" type="date" />
                  <label for="time">Time</label>
                  <input id="time" type="time" />
                  <button type="button" onclick="createSession()">Create session request</button>
                  <div id="session_status" role="status" aria-live="polite"></div>
                </div>

                <div class="card">
                  <div class="card-head"><span class="card-title">Evidence links</span><span class="card-note">Read-only probes</span></div>
                  <div class="links"><a href="/health">health</a><a href="/demo">CLI demo output</a><a href="/?format=json">API metadata</a></div>
                </div>

                <div class="card">
                  <div class="card-head"><span class="card-title">Session ledger</span><span class="card-note">Current account</span></div>
                  <div id="sessions" style="margin-top:8px"></div>
                  <button type="button" class="secondary" onclick="loadSessions()">Refresh ledger</button>
                </div>
              </div>
            </div>
            <div class="footer-line"><span>YOR / matching workflow</span><span>VERIFIED API · DEMO CLIENT · LOCAL GUI</span></div>

            <script>
              async function login(){
                const roll = document.getElementById('roll').value.trim();
                const pass = document.getElementById('pass').value;
                if(!roll||!pass){document.getElementById('status').innerText='Enter roll and password';return}
                const res = await fetch('/token',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({roll_no:roll,password:pass})});
                const data = await res.json().catch(()=>({ok:false,error:'Invalid response'}));
                if(res.ok && data.ok){
                  document.getElementById('status').innerText = 'Logged in: '+(data.user.name||data.user.roll_no);
                  window.currentUser = data.user;
                  window.token = data.token;
                  document.getElementById('mentee_id').value = data.user.user_id || '';
                } else {
                  document.getElementById('status').innerText = data.error || 'Login failed';
                }
                loadMentors();
                loadSessions();
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
                        el.tabIndex = 0;
                        el.setAttribute('role', 'button');
                        el.onclick = ()=> document.getElementById('mentor_id').value = m.user_id;
                        el.onkeydown = (event)=> { if(event.key === 'Enter' || event.key === ' '){ event.preventDefault(); el.click(); } };
                        container.appendChild(el);
                  })
                } else {
                  container.textContent = 'No mentors available.';
                }
              }

              function getAuthHeaders(){ return window.token ? {'Authorization':'Bearer '+window.token} : {}; }

              async function createSession(){
                const mentor_id = document.getElementById('mentor_id').value.trim();
                const mentee_id = (window.currentUser && window.currentUser.user_id) || document.getElementById('mentee_id').value.trim();
                const date = document.getElementById('date').value;
                const time = document.getElementById('time').value;
                if(!mentor_id||!mentee_id||!date||!time){document.getElementById('session_status').innerText='Please fill all fields';return}
                const headers = Object.assign({'Content-Type':'application/json'}, getAuthHeaders());
                const res = await fetch('/sessions',{method:'POST',headers:headers,body:JSON.stringify({mentor_id,mentee_id,date,time})});
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
                    const res = await fetch(url, { headers: getAuthHeaders() });
                    const data = await res.json().catch(()=>({ok:false}));
                    const container = document.getElementById('sessions');
                    container.innerHTML = '';
                    if(data.ok && Array.isArray(data.sessions) && data.sessions.length){
                      data.sessions.forEach(s=>{
                        const el = document.createElement('div');
                        el.className = 'session-row';

                        const left = document.createElement('span');
                        left.className = 'session-copy';
                        left.textContent = `${s.session_id || ''} — ${s.topic || s.concern || ''} — ${s.date || ''} ${s.time || ''} (${s.status || ''})`;
                        el.appendChild(left);

                        if((s.status||'').toLowerCase() !== 'cancelled' && (s.status||'').toLowerCase() !== 'completed'){
                          const btn = document.createElement('button');
                          btn.type = 'button';
                          btn.textContent = 'Cancel';
                          btn.onclick = async ()=>{
                            if(!confirm('Cancel session ' + (s.session_id||'') + '?')) return;
                            try{
                              const res = await fetch(`/sessions/${encodeURIComponent(s.session_id)}/cancel`, { method: 'POST', headers: getAuthHeaders() });
                              const j = await res.json().catch(()=>({ok:false}));
                              if(res.ok && j.ok){
                                loadSessions();
                              } else {
                                alert(j.error || 'Failed to cancel session');
                              }
                            } catch(e){
                              alert('Network error while cancelling');
                            }
                          };
                          el.appendChild(btn);
                        }

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


logging.basicConfig(level=logging.INFO)


def require_auth(func):
  @wraps(func)
  def wrapper(*args, **kwargs):
    auth_header = request.headers.get("Authorization", "") or request.headers.get("authorization", "")
    if not auth_header.startswith("Bearer "):
      return jsonify({"ok": False, "error": "missing token"}), 401
    token = auth_header.split(None, 1)[1]
    payload = auth.decode_token(token)
    if not payload:
      return jsonify({"ok": False, "error": "invalid token"}), 401
    user = database.get_user_by_id(payload.get("user_id"))
    if not user:
      return jsonify({"ok": False, "error": "user not found"}), 404
    g.current_user = {k: v for k, v in user.items() if k != "password"}
    return func(*args, **kwargs)
  return wrapper


@app.post("/token")
def http_token():
  data = request.get_json(silent=True) or {}
  roll_no = data.get("roll_no") or data.get("roll") or data.get("username")
  password = data.get("password", "")
  if not roll_no or not password:
    return jsonify({"ok": False, "error": "missing credentials"}), 400
  ok, user = auth.login(roll_no, password)
  if not ok:
    return jsonify({"ok": False, "error": "invalid credentials"}), 401
  token = auth.generate_token(user.get("user_id"))
  return jsonify({"ok": True, "token": token, "user": user})


@app.get("/me")
def http_me():
  auth_header = request.headers.get("Authorization", "") or request.headers.get("authorization", "")
  if not auth_header.startswith("Bearer "):
    return jsonify({"ok": False, "error": "missing token"}), 401
  token = auth_header.split(None, 1)[1]
  payload = auth.decode_token(token)
  if not payload:
    return jsonify({"ok": False, "error": "invalid token"}), 401
  user = database.get_user_by_id(payload.get("user_id"))
  if not user:
    return jsonify({"ok": False, "error": "user not found"}), 404
  safe = {k: v for k, v in user.items() if k != "password"}
  return jsonify({"ok": True, "user": safe})


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

    # Check uniqueness
    if database.get_user_by_roll_no(data.get("roll_no")):
        return jsonify({"ok": False, "error": "roll_no already exists"}), 409
    if database.get_user_by_email(data.get("email")):
        return jsonify({"ok": False, "error": "email already exists"}), 409

    # Validate password strength
    ok_pw, reason = auth._strong_password(pwd)
    if not ok_pw:
        return jsonify({"ok": False, "error": reason}), 400

    hashed = auth.hash_password(pwd)
    role = data.get("role", "mentee")
    if role not in ("mentee", "mentor"):
        role = "mentee"

    user = {
        "name": data.get("name"),
        "roll_no": data.get("roll_no"),
        "email": data.get("email"),
        "role": role,
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
@require_auth
def http_update_session(session_id):
    data = request.get_json(silent=True) or {}
    updated = database.update_session(session_id, data)
    if not updated:
        return jsonify({"ok": False, "error": "not found"}), 404
    return jsonify({"ok": True, "session": updated})


@app.post("/sessions")
@require_auth
def http_create_session():
    data = request.get_json(silent=True) or {}
    required = ("mentor_id", "mentee_id", "date", "time")
    if not all(k in data for k in required):
        return jsonify({"ok": False, "error": "missing fields"}), 400
    session = database.create_session(data)
    return jsonify({"ok": True, "session": session}), 201


@app.post("/sessions/<session_id>/cancel")
@require_auth
def http_cancel_session(session_id):
    updated = database.update_session(session_id, {"status": "cancelled", "resolved_at": database.now_iso()})
    if not updated:
        return jsonify({"ok": False, "error": "not found"}), 404
    return jsonify({"ok": True, "session": updated})


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
@require_auth
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
@require_auth
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
