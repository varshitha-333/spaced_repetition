"""
Simple dev server that serves the React frontend static build
and provides a demo API for testing the UI without Supabase/Google credentials.
"""
import os
import json
import uuid
from datetime import datetime, date, timedelta
from flask import Flask, request, jsonify, session, send_from_directory
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__, static_folder='frontend/dist', static_url_path='')
app.secret_key = 'demo-secret-key-for-testing'
CORS(app, supports_credentials=True)

# ─── In-memory demo data ───
DEMO_USERS = {}
DEMO_LEARNINGS = {}
DEMO_REVISIONS = {}
DEMO_STATES = {}

REVISION_INTERVALS = [1, 3, 6, 29, 179]

def seed_demo():
    uid = 'demo-user-1'
    DEMO_USERS['demo'] = {
        'id': uid, 'username': 'demo',
        'email': 'demo@learnflow.app',
        'password_hash': generate_password_hash('demo123')
    }
    DEMO_STATES[uid] = {'drive_connected': False, 'current_streak': 3, 'last_completion_date': date.today().isoformat()}

    # Sample learnings
    samples = [
        ("Data Structures & Algorithms", "Binary trees, hash maps, and graph traversal fundamentals", "file"),
        ("Machine Learning Basics", "Supervised vs unsupervised learning, neural network architecture", "url"),
        ("React Hooks Deep Dive", "useState, useEffect, useContext, custom hooks patterns", "text"),
        ("Python Decorators", "Function decorators, class decorators, and decorator patterns", "file"),
    ]
    today = date.today()
    for i, (title, content, src) in enumerate(samples):
        lid = f'learning-{i+1}'
        DEMO_LEARNINGS[lid] = {
            'id': lid, 'user_id': uid, 'title': title, 'content': content,
            'source_type': src, 'source_name': f'sample_{i}.pdf',
            'created_at': (today - timedelta(days=i*5)).isoformat(),
            'revision_stage': min(i+1, 5), 'drive_link': None,
        }
        # Create revisions (some today, some upcoming)
        for stage_idx, interval in enumerate(REVISION_INTERVALS):
            rid = f'rev-{lid}-{stage_idx+1}'
            sched = today + timedelta(days=interval - (i * 2))
            completed = sched < today
            DEMO_REVISIONS[rid] = {
                'id': rid, 'user_id': uid, 'learning_id': lid,
                'heading': title, 'description': content,
                'drive_link': 'https://drive.google.com/file/d/example/view' if i == 0 else None,
                'url': 'https://example.com/article' if src == 'url' else None,
                'supabase_path': None, 'supabase_url': None,
                'stage': stage_idx + 1, 'total_stages': 5,
                'scheduled_date': sched.isoformat(),
                'completed': completed,
                'completed_date': sched.isoformat() if completed else None,
                'notes': f'Stage {stage_idx+1} - {interval} day revision',
            }

seed_demo()


# ─── AUTH ───
@app.route('/api/auth/register', methods=['POST'])
def register():
    d = request.get_json()
    uname = d.get('username', '').strip()
    pw = d.get('password', '').strip()
    email = d.get('email', '').strip()
    if not uname or not pw or not email:
        return jsonify({"error": "All fields required"}), 400
    if uname in DEMO_USERS:
        return jsonify({"error": "Username exists"}), 400
    uid = str(uuid.uuid4())
    DEMO_USERS[uname] = {'id': uid, 'username': uname, 'email': email, 'password_hash': generate_password_hash(pw)}
    DEMO_STATES[uid] = {'drive_connected': False, 'current_streak': 0, 'last_completion_date': None}
    return jsonify({"message": "Registration successful"}), 201

@app.route('/api/auth/login', methods=['POST'])
def login():
    d = request.get_json()
    uname = d.get('username', '').strip()
    pw = d.get('password', '').strip()
    user = DEMO_USERS.get(uname)
    if user and check_password_hash(user['password_hash'], pw):
        session['user_id'] = user['id']
        session['username'] = uname
        return jsonify({"message": "Login successful", "user": {"id": user['id'], "username": uname, "email": user['email']}})
    return jsonify({"error": "Invalid credentials"}), 401

@app.route('/api/auth/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({"message": "Logged out"})

@app.route('/api/auth/me')
def me():
    uid = session.get('user_id')
    if uid:
        uname = session.get('username')
        st = DEMO_STATES.get(uid, {})
        return jsonify({"user": {"id": uid, "username": uname, "drive_connected": st.get('drive_connected', False)}})
    return jsonify({"user": None}), 401

@app.route('/api/auth/google')
def google_auth():
    return jsonify({"auth_url": "#", "message": "Google OAuth requires real credentials. Use username/password for demo."})

@app.route('/api/drive/connect')
def drive_connect():
    return jsonify({"auth_url": "#", "message": "Drive connection requires Google credentials."})

@app.route('/api/drive/disconnect', methods=['POST'])
def drive_disconnect():
    uid = session.get('user_id')
    if uid and uid in DEMO_STATES:
        DEMO_STATES[uid]['drive_connected'] = False
    return jsonify({"message": "Disconnected"})


# ─── UPLOAD ───
@app.route('/api/upload/preview', methods=['POST'])
def preview():
    if 'user_id' not in session:
        return jsonify({"error": "Auth required"}), 401
    # Simulate AI-generated preview
    file = request.files.get('file')
    url = request.form.get('url', '').strip()
    text = request.form.get('text', '').strip()
    if file:
        heading = f"Notes: {file.filename.rsplit('.', 1)[0][:40]}"
        desc = "AI-generated summary of the uploaded document content."
        return jsonify({"heading": heading, "description": desc, "source": "file", "filename": file.filename, "content_snippet": "Content extracted from file..."})
    elif url:
        heading = "Web Article Summary"
        desc = f"Key insights extracted from {url[:60]}"
        return jsonify({"heading": heading, "description": desc, "source": "url", "url": url, "content_snippet": "Content from URL..."})
    elif text:
        heading = text[:50].strip() + ('...' if len(text) > 50 else '')
        desc = "Summary of pasted text content."
        return jsonify({"heading": heading, "description": desc, "source": "text", "content_snippet": text[:500]})
    return jsonify({"error": "No content"}), 400

@app.route('/api/upload/save', methods=['POST'])
def save():
    uid = session.get('user_id')
    if not uid:
        return jsonify({"error": "Auth required"}), 401
    d = request.get_json()
    heading = d.get('heading', 'Untitled')
    desc = d.get('description', '')
    source = d.get('source', 'text')
    lid = str(uuid.uuid4())[:8]
    DEMO_LEARNINGS[lid] = {
        'id': lid, 'user_id': uid, 'title': heading, 'content': desc,
        'source_type': source, 'source_name': d.get('filename', 'manual'),
        'created_at': datetime.now().isoformat(), 'revision_stage': 1, 'drive_link': None,
    }
    today = date.today()
    for i, interval in enumerate(REVISION_INTERVALS):
        rid = str(uuid.uuid4())[:8]
        DEMO_REVISIONS[rid] = {
            'id': rid, 'user_id': uid, 'learning_id': lid,
            'heading': heading, 'description': desc,
            'drive_link': None, 'url': d.get('url'), 'supabase_path': None, 'supabase_url': None,
            'stage': i + 1, 'total_stages': 5,
            'scheduled_date': (today + timedelta(days=interval)).isoformat(),
            'completed': False, 'completed_date': None,
            'notes': f'Stage {i+1} - {interval} day revision',
        }
    return jsonify({"message": "Saved!", "learning_id": lid}), 201


# ─── REVISIONS ───
def _user_revisions(uid):
    return [r for r in DEMO_REVISIONS.values() if r['user_id'] == uid]

@app.route('/api/revisions/today')
def today_revisions():
    uid = session.get('user_id')
    if not uid: return jsonify({"error": "Auth"}), 401
    today = date.today().isoformat()
    return jsonify([r for r in _user_revisions(uid) if r['scheduled_date'] == today and not r['completed']])

@app.route('/api/revisions/overdue')
def overdue_revisions():
    uid = session.get('user_id')
    if not uid: return jsonify({"error": "Auth"}), 401
    today = date.today().isoformat()
    return jsonify([r for r in _user_revisions(uid) if r['scheduled_date'] < today and not r['completed']])

@app.route('/api/revisions/completed')
def completed_revisions():
    uid = session.get('user_id')
    if not uid: return jsonify({"error": "Auth"}), 401
    today = date.today().isoformat()
    return jsonify([r for r in _user_revisions(uid) if r['completed'] and r.get('completed_date') == today])

@app.route('/api/revisions/upcoming')
def upcoming_revisions():
    uid = session.get('user_id')
    if not uid: return jsonify({"error": "Auth"}), 401
    tomorrow = (date.today() + timedelta(days=1)).isoformat()
    revs = [r for r in _user_revisions(uid) if r['scheduled_date'] >= tomorrow and not r['completed']]
    revs.sort(key=lambda x: x['scheduled_date'])
    grouped = {}
    for r in revs:
        grouped.setdefault(r['scheduled_date'], []).append(r)
    return jsonify({"grouped": grouped, "total": len(revs)})

@app.route('/api/revisions/stats')
def revision_stats():
    uid = session.get('user_id')
    if not uid: return jsonify({"error": "Auth"}), 401
    today_str = date.today().isoformat()
    tomorrow_str = (date.today() + timedelta(days=1)).isoformat()
    revs = _user_revisions(uid)
    st = DEMO_STATES.get(uid, {})
    return jsonify({
        "today": len([r for r in revs if r['scheduled_date'] == today_str and not r['completed']]),
        "overdue": len([r for r in revs if r['scheduled_date'] < today_str and not r['completed']]),
        "completed_today": len([r for r in revs if r['completed'] and r.get('completed_date') == today_str]),
        "tomorrow": len([r for r in revs if r['scheduled_date'] == tomorrow_str and not r['completed']]),
        "future": len([r for r in revs if r['scheduled_date'] > tomorrow_str and not r['completed']]),
        "streak": st.get('current_streak', 0),
    })

@app.route('/api/revisions/<rid>/complete', methods=['POST'])
def complete(rid):
    uid = session.get('user_id')
    if not uid: return jsonify({"error": "Auth"}), 401
    if rid in DEMO_REVISIONS and DEMO_REVISIONS[rid]['user_id'] == uid:
        DEMO_REVISIONS[rid]['completed'] = True
        DEMO_REVISIONS[rid]['completed_date'] = date.today().isoformat()
        return jsonify({"message": "Completed!"})
    return jsonify({"error": "Not found"}), 404

@app.route('/api/revisions/<rid>/postpone', methods=['POST'])
def postpone(rid):
    uid = session.get('user_id')
    if not uid: return jsonify({"error": "Auth"}), 401
    if rid in DEMO_REVISIONS and DEMO_REVISIONS[rid]['user_id'] == uid:
        DEMO_REVISIONS[rid]['scheduled_date'] = (date.today() + timedelta(days=1)).isoformat()
        return jsonify({"message": "Postponed"})
    return jsonify({"error": "Not found"}), 404

@app.route('/api/revisions/<rid>/skip', methods=['POST'])
def skip(rid):
    uid = session.get('user_id')
    if not uid: return jsonify({"error": "Auth"}), 401
    if rid in DEMO_REVISIONS and DEMO_REVISIONS[rid]['user_id'] == uid:
        cur = DEMO_REVISIONS[rid]['scheduled_date']
        new = (datetime.strptime(cur, "%Y-%m-%d").date() + timedelta(days=1)).isoformat()
        DEMO_REVISIONS[rid]['scheduled_date'] = new
        return jsonify({"message": f"Skipped to {new}"})
    return jsonify({"error": "Not found"}), 404


# ─── LEARNINGS ───
@app.route('/api/learnings')
def learnings():
    uid = session.get('user_id')
    if not uid: return jsonify({"error": "Auth"}), 401
    items = [l for l in DEMO_LEARNINGS.values() if l['user_id'] == uid]
    items.sort(key=lambda x: x.get('created_at', ''), reverse=True)
    return jsonify(items)


# ─── HEALTH ───
@app.route('/api/health')
def health():
    return jsonify({"status": "ok"})


# ─── SERVE REACT SPA ───
@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve_react(path):
    if path and os.path.exists(os.path.join(app.static_folder, path)):
        return send_from_directory(app.static_folder, path)
    return send_from_directory(app.static_folder, 'index.html')


if __name__ == '__main__':
    print("\n" + "="*60)
    print("  LearnFlow Demo Server")
    print("  Login: username=demo  password=demo123")
    print("="*60 + "\n")
    app.run(host='0.0.0.0', port=3000, debug=False)
