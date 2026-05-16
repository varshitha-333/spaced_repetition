import os
import time
from datetime import datetime, date, timedelta
from pathlib import Path
import requests
from bs4 import BeautifulSoup
from flask import Flask, request, jsonify, session
from flask_cors import CORS
from PyPDF2 import PdfReader
from docx import Document
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.oauth2.credentials import Credentials
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from functools import wraps
from supabase import create_client, Client
from dotenv import load_dotenv
import logging
import uuid
import json
import io
from tempfile import NamedTemporaryFile
import urllib.parse

load_dotenv()

logging.getLogger('googleapiclient.discovery_cache').setLevel(logging.ERROR)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ─── CONFIG ───
SCOPES = [
    "https://www.googleapis.com/auth/drive.file",
    "https://www.googleapis.com/auth/spreadsheets"
]

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
SUPABASE_BUCKET = os.getenv("SUPABASE_BUCKET", "learning-intake-uploads")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

GOOGLE_OAUTH_CLIENT_ID = os.getenv("GOOGLE_OAUTH_CLIENT_ID")
GOOGLE_OAUTH_CLIENT_SECRET = os.getenv("GOOGLE_OAUTH_CLIENT_SECRET")
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:5000")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")
APP_FOLDER_NAME = "Learning Intake"
SHEET_TITLE = "Learning Intake Log"
REVISION_INTERVALS = [1, 3, 6, 29, 179]

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "change-this-to-a-strong-secret-in-production")
app.config['SESSION_COOKIE_SAMESITE'] = 'None'
app.config['SESSION_COOKIE_SECURE'] = True

CORS(app, supports_credentials=True, origins=[
    FRONTEND_URL,
    "http://localhost:5173",
    "http://localhost:3000",
])

# ─── BUCKET SETUP ───
def ensure_bucket_exists():
    try:
        buckets = supabase.storage.list_buckets()
        bucket_names = [b.name for b in buckets]
        if SUPABASE_BUCKET not in bucket_names:
            supabase.storage.create_bucket(
                SUPABASE_BUCKET,
                options={
                    "public": False,
                    "file_size_limit": 52428800,
                    "allowed_mime_types": [
                        "application/pdf",
                        "application/msword",
                        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                        "text/plain",
                        "text/markdown",
                        "application/octet-stream"
                    ]
                }
            )
        return True
    except Exception as e:
        logger.error(f"Bucket setup error: {e}")
        return False


# ─── AUTH HELPERS ───
def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({"error": "Authentication required"}), 401
        return f(*args, **kwargs)
    return decorated

@app.route("/privacy")
def privacy():
    return "privacy policy"
# ─── DATABASE HELPERS ───
def get_user_by_username(username):
    try:
        r = supabase.table('users').select('*').eq('username', username).execute()
        return r.data[0] if r.data else None
    except:
        return None

def get_user_by_email(email):
    try:
        r = supabase.table('users').select('*').eq('email', email).execute()
        return r.data[0] if r.data else None
    except:
        return None

def create_user(username, password_hash, email):
    try:
        r = supabase.table('users').insert({
            'username': username,
            'password_hash': password_hash,
            'email': email
        }).execute()
        uid = r.data[0]['id']
        supabase.table('user_state').insert({
            'user_id': uid,
            'drive_connected': False,
            'spreadsheet_id': None,
            'current_streak': 0,
            'last_completion_date': None,
            'google_drive_credentials': None
        }).execute()
        return uid
    except Exception as e:
        logger.error(f"Create user error: {e}")
        return None

def get_user_state(user_id):
    try:
        r = supabase.table('user_state').select('*').eq('user_id', user_id).execute()
        return r.data[0] if r.data else None
    except:
        return None

def update_user_state(user_id, **kwargs):
    try:
        supabase.table('user_state').update(kwargs).eq('user_id', user_id).execute()
        return True
    except:
        return False

def save_drive_credentials(user_id, creds_json):
    try:
        supabase.table('user_state').update({
            'google_drive_credentials': creds_json,
            'drive_connected': True
        }).eq('user_id', user_id).execute()
        return True
    except:
        return False

def get_drive_credentials(user_id):
    try:
        r = supabase.table('user_state').select('google_drive_credentials').eq('user_id', user_id).execute()
        if r.data and r.data[0]['google_drive_credentials']:
            return r.data[0]['google_drive_credentials']
        return None
    except:
        return None


# ─── SUPABASE STORAGE ───
def sanitize_filename(filename):
    safe = secure_filename(filename)
    safe = safe.replace('%', '_').replace('#', '_').replace('&', '_')
    name, ext = os.path.splitext(safe)
    return f"{name[:100]}{ext}"

def upload_to_supabase(user_id, file_data, filename):
    try:
        ensure_bucket_exists()
        safe = sanitize_filename(filename)
        path = f"{user_id}/{uuid.uuid4().hex}_{safe}"
        ext = Path(safe).suffix.lower()
        ct_map = {
            '.pdf': 'application/pdf',
            '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            '.doc': 'application/msword',
            '.txt': 'text/plain',
            '.md': 'text/markdown'
        }
        ct = ct_map.get(ext, 'application/octet-stream')
        supabase.storage.from_(SUPABASE_BUCKET).upload(path, file_data, file_options={"content-type": ct})
        try:
            supabase.table('uploaded_files').insert({
                'user_id': user_id,
                'filename': safe,
                'supabase_path': path,
                'upload_date': datetime.utcnow().isoformat()
            }).execute()
        except:
            pass
        return path
    except Exception as e:
        logger.error(f"Upload error: {e}")
        return None

def download_from_supabase(path):
    try:
        return supabase.storage.from_(SUPABASE_BUCKET).download(path)
    except:
        return None

def get_supabase_url(path):
    try:
        r = supabase.storage.from_(SUPABASE_BUCKET).create_signed_url(path, expires_in=3600)
        return r.get('signedURL')
    except:
        return None

def cleanup_old_files(user_id):
    try:
        cutoff = (datetime.utcnow() - timedelta(days=10)).isoformat()
        old = supabase.table('uploaded_files').select('*').eq('user_id', user_id).lt('upload_date', cutoff).execute()
        if not old.data:
            return
        for f in old.data:
            try:
                supabase.storage.from_(SUPABASE_BUCKET).remove([f['supabase_path']])
            except:
                pass
            try:
                supabase.table('uploaded_files').delete().eq('id', f['id']).execute()
            except:
                pass
    except:
        pass


# ─── STREAK ───
def get_user_streak(user_id):
    state = get_user_state(user_id)
    if state:
        return state.get('current_streak', 0), state.get('last_completion_date')
    return 0, None

def update_streak(user_id):
    try:
        today = date.today().isoformat()
        due = supabase.table('revisions').select('id').eq('user_id', user_id).eq('scheduled_date', today).eq('completed', False).execute()
        overdue = supabase.table('revisions').select('id').eq('user_id', user_id).lt('scheduled_date', today).eq('completed', False).execute()
        streak, last = get_user_streak(user_id)
        if len(due.data) == 0 and len(overdue.data) == 0:
            tasks = supabase.table('revisions').select('id').eq('user_id', user_id).eq('scheduled_date', today).execute()
            if tasks.data:
                if last:
                    diff = (date.today() - datetime.strptime(last, "%Y-%m-%d").date()).days
                    streak = streak + 1 if diff == 1 else 1
                else:
                    streak = 1
                update_user_state(user_id, current_streak=streak, last_completion_date=today)
        return streak
    except:
        return 0


# ─── REVISIONS ───
def schedule_revisions(user_id, item_id, heading, description, drive_link=None, url=None, supabase_path=None):
    try:
        today = date.today()
        for i, interval in enumerate(REVISION_INTERVALS, 1):
            sd = today + timedelta(days=interval)
            supabase.table('revisions').insert({
                'user_id': user_id,
                'learning_id': item_id,
                'heading': heading,
                'description': description,
                'drive_link': drive_link,
                'url': url,
                'supabase_path': supabase_path,
                'stage': i,
                'scheduled_date': sd.isoformat(),
                'completed': False,
                'notes': f"Stage {i} - {interval} day revision"
            }).execute()
        first_date = today + timedelta(days=REVISION_INTERVALS[0])
        supabase.table('learnings').update({
            'revision_stage': 1,
            'next_revision_date': first_date.isoformat()
        }).eq('id', item_id).execute()
        return True
    except Exception as e:
        logger.error(f"Schedule error: {e}")
        return False

def get_revision_stats(user_id):
    try:
        today = date.today().isoformat()
        tomorrow = (date.today() + timedelta(days=1)).isoformat()
        due = len(supabase.table('revisions').select('id').eq('user_id', user_id).eq('scheduled_date', today).eq('completed', False).execute().data)
        overdue = len(supabase.table('revisions').select('id').eq('user_id', user_id).lt('scheduled_date', today).eq('completed', False).execute().data)
        done = len(supabase.table('revisions').select('id').eq('user_id', user_id).eq('completed_date', today).execute().data)
        tmr = len(supabase.table('revisions').select('id').eq('user_id', user_id).eq('scheduled_date', tomorrow).eq('completed', False).execute().data)
        future = len(supabase.table('revisions').select('id').eq('user_id', user_id).gt('scheduled_date', tomorrow).eq('completed', False).execute().data)
        return {"today": due, "overdue": overdue, "completed_today": done, "tomorrow": tmr, "future": future}
    except:
        return {"today": 0, "overdue": 0, "completed_today": 0, "tomorrow": 0, "future": 0}

def _build_revision(row):
    obj = {
        "id": row['id'],
        "learning_id": row.get('learning_id'),
        "heading": row.get('heading', 'Untitled'),
        "description": row.get('description', 'No description'),
        "drive_link": row.get('drive_link'),
        "url": row.get('url'),
        "supabase_path": row.get('supabase_path'),
        "stage": row.get('stage', 1),
        "scheduled_date": row.get('scheduled_date'),
        "notes": row.get('notes', ''),
        "total_stages": len(REVISION_INTERVALS),
    }
    if not obj['drive_link'] and row.get('supabase_path'):
        obj['supabase_url'] = get_supabase_url(row['supabase_path'])
    else:
        obj['supabase_url'] = None
    return obj


# ─── GEMINI CLIENT ───
class GeminiClient:
    def __init__(self):
        self.model = "gemini-2.5-flash"
        self.api_url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent"
        self.api_key = os.getenv("GEMINI_API_KEY")
        self.headers = {"Content-Type": "application/json"}

    def generate(self, snippet):
        if not snippet or not snippet.strip():
            return "Untitled Item", "No content provided."
        if not self.api_key:
            return "Generated Title", "AI generation not configured."
        payload = {
            "contents": [{"parts": [{"text": (
                "Generate concise learning metadata.\n\n"
                "Rules:\n- Heading: max 8 words\n- Description: 1-2 short sentences\n"
                "- No markdown or labels\n\n"
                f"Content:\n{snippet[:1500]}"
            )}]}]
        }
        try:
            r = requests.post(self.api_url, headers=self.headers, params={"key": self.api_key}, json=payload, timeout=30)
            r.raise_for_status()
            text = r.json()["candidates"][0]["content"]["parts"][0]["text"]
            lines = [l.strip() for l in text.splitlines() if l.strip()]
            heading = lines[0] if lines else "Untitled"
            desc = " ".join(lines[1:]) if len(lines) > 1 else "Brief summary."
            return heading, desc
        except:
            return "Generated Heading", "Auto-description failed."

gemini = GeminiClient()


# ─── FILE HELPERS ───
def extract_text(file_data, filename):
    ext = Path(filename).suffix.lower()
    text = ""
    try:
        if ext == ".pdf":
            with NamedTemporaryFile(delete=False, suffix='.pdf') as tmp:
                tmp.write(file_data)
                tp = tmp.name
            reader = PdfReader(tp)
            text = " ".join((p.extract_text() or "").replace("\udcff", "?") for p in reader.pages[:5])
            os.unlink(tp)
        elif ext in [".docx", ".doc"]:
            with NamedTemporaryFile(delete=False, suffix=ext) as tmp:
                tmp.write(file_data)
                tp = tmp.name
            doc = Document(tp)
            text = " ".join(p.text for p in doc.paragraphs[:60])
            os.unlink(tp)
        elif ext in [".txt", ".md"]:
            text = file_data.decode('utf-8', errors='ignore')[:5000]
        else:
            text = f"[Unsupported: {filename}]"
    except Exception as e:
        text = f"[Error: {e}]"
    return text[:3000]

def extract_from_url(url):
    try:
        r = requests.get(url, timeout=12, headers={"User-Agent": "Mozilla/5.0"})
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")
        for tag in soup(["script", "style"]):
            tag.decompose()
        return " ".join(p.get_text() for p in soup.find_all("p"))[:2500]
    except:
        return "(Failed to load URL)"


# ─── GOOGLE DRIVE ───
def _build_creds(user_id):
    cj = get_drive_credentials(user_id)
    if not cj:
        return None
    try:
        data = json.loads(cj) if isinstance(cj, str) else cj
        return Credentials(
            token=data.get("token"),
            refresh_token=data.get("refresh_token"),
            token_uri=data.get("token_uri"),
            client_id=data.get("client_id"),
            client_secret=data.get("client_secret"),
            scopes=data.get("scopes") or SCOPES
        )
    except:
        return None

def get_drive_service(user_id):
    creds = _build_creds(user_id)
    return build("drive", "v3", credentials=creds) if creds else None

def get_sheets_service(user_id):
    creds = _build_creds(user_id)
    return build("sheets", "v4", credentials=creds) if creds else None

def get_or_create_folder(service):
    if not service:
        return None
    try:
        r = service.files().list(
            q=f"name='{APP_FOLDER_NAME}' and mimeType='application/vnd.google-apps.folder' and trashed=false",
            fields="files(id)"
        ).execute()
        files = r.get("files", [])
        if files:
            return files[0]["id"]
        f = service.files().create(
            body={"name": APP_FOLDER_NAME, "mimeType": "application/vnd.google-apps.folder"},
            fields="id"
        ).execute()
        return f["id"]
    except:
        return None

def upload_to_drive(user_id, supabase_path, filename):
    try:
        service = get_drive_service(user_id)
        if not service:
            return None
        folder_id = get_or_create_folder(service)
        if not folder_id:
            return None
        data = download_from_supabase(supabase_path)
        if not data:
            return None
        with NamedTemporaryFile(delete=False) as tmp:
            tmp.write(data)
            tp = tmp.name
        media = MediaFileUpload(tp, resumable=True)
        uploaded = service.files().create(
            body={"name": filename, "parents": [folder_id]},
            media_body=media, fields="id"
        ).execute()
        service.permissions().create(
            fileId=uploaded["id"],
            body={"type": "anyone", "role": "reader"}
        ).execute()
        os.unlink(tp)
        return f"https://drive.google.com/file/d/{uploaded['id']}/view"
    except Exception as e:
        logger.error(f"Drive upload error: {e}")
        return None

def append_to_sheet(user_id, data):
    service = get_sheets_service(user_id)
    if not service:
        return
    state = get_user_state(user_id)
    sid = state.get('spreadsheet_id') if state else None
    if not sid:
        ss = service.spreadsheets().create(
            body={"properties": {"title": SHEET_TITLE}, "sheets": [{"properties": {"title": "Log"}}]}
        ).execute()
        sid = ss["spreadsheetId"]
        service.spreadsheets().values().update(
            spreadsheetId=sid, range="Log!A1", valueInputOption="RAW",
            body={"values": [["Date", "Time", "Heading", "Description", "Type", "Source", "Drive Link", "URL"]]}
        ).execute()
        update_user_state(user_id, spreadsheet_id=sid)
    now = datetime.now()
    service.spreadsheets().values().append(
        spreadsheetId=sid, range="Log!A1", valueInputOption="RAW", insertDataOption="INSERT_ROWS",
        body={"values": [[
            now.strftime("%Y-%m-%d"), now.strftime("%H:%M:%S"),
            data["heading"], data.get("description", ""),
            data["input_type"], data["source"],
            data.get("drive_link", ""), data.get("url", "")
        ]]}
    ).execute()


# ═══════════════════════════════════════════════════════
#                      API ROUTES
# ═══════════════════════════════════════════════════════

# ─── AUTH ───
@app.route("/api/auth/register", methods=["POST"])
def api_register():
    data = request.get_json()
    username = data.get("username", "").strip()
    password = data.get("password", "").strip()
    email = data.get("email", "").strip()
    if not username or not password or not email:
        return jsonify({"error": "All fields required"}), 400
    if get_user_by_username(username):
        return jsonify({"error": "Username already exists"}), 400
    if get_user_by_email(email):
        return jsonify({"error": "Email already registered"}), 400
    uid = create_user(username, generate_password_hash(password), email)
    if uid:
        return jsonify({"message": "Registration successful"}), 201
    return jsonify({"error": "Registration failed"}), 500

@app.route("/api/auth/login", methods=["POST"])
def api_login():
    data = request.get_json()
    username = data.get("username", "").strip()
    password = data.get("password", "").strip()
    if not username or not password:
        return jsonify({"error": "Credentials required"}), 400
    user = get_user_by_username(username)
    if user and check_password_hash(user['password_hash'], password):
        session['user_id'] = user['id']
        session['username'] = username
        return jsonify({"message": "Login successful", "user": {"id": user['id'], "username": username, "email": user.get('email')}})
    return jsonify({"error": "Invalid credentials"}), 401

@app.route("/api/auth/logout", methods=["POST"])
def api_logout():
    session.clear()
    return jsonify({"message": "Logged out"})

@app.route("/api/auth/me")
def api_me():
    if 'user_id' in session:
        state = get_user_state(session['user_id'])
        dc = False
        if state and state.get('drive_connected'):
            cj = get_drive_credentials(session['user_id'])
            dc = cj is not None
        return jsonify({
            "user": {
                "id": session['user_id'],
                "username": session.get('username'),
                "drive_connected": dc
            }
        })
    return jsonify({"user": None}), 401


# ─── GOOGLE AUTH (Sign in with Google) ───
@app.route("/api/auth/google")
def api_google_auth():
    flow = Flow.from_client_config({
        "web": {
            "client_id": GOOGLE_OAUTH_CLIENT_ID,
            "client_secret": GOOGLE_OAUTH_CLIENT_SECRET,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [f"{BACKEND_URL}/api/auth/google/callback"]
        }
    }, scopes=["openid", "https://www.googleapis.com/auth/userinfo.email", "https://www.googleapis.com/auth/userinfo.profile"])
    flow.redirect_uri = f"{BACKEND_URL}/api/auth/google/callback"
    url, state = flow.authorization_url(access_type="offline", prompt="consent")
    session["google_auth_state"] = state
    return jsonify({"auth_url": url})

@app.route("/api/auth/google/callback")
def api_google_callback():
    state = session.get("google_auth_state")
    flow = Flow.from_client_config({
        "web": {
            "client_id": GOOGLE_OAUTH_CLIENT_ID,
            "client_secret": GOOGLE_OAUTH_CLIENT_SECRET,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [f"{BACKEND_URL}/api/auth/google/callback"]
        }
    }, scopes=["openid", "https://www.googleapis.com/auth/userinfo.email", "https://www.googleapis.com/auth/userinfo.profile"], state=state)
    flow.redirect_uri = f"{BACKEND_URL}/api/auth/google/callback"
    flow.fetch_token(authorization_response=request.url)
    creds = flow.credentials
    info = requests.get('https://www.googleapis.com/oauth2/v3/userinfo', headers={'Authorization': f'Bearer {creds.token}'}).json()
    email = info.get('email')
    user = get_user_by_email(email)
    if not user:
        uname = email.split('@')[0] + '_' + uuid.uuid4().hex[:8]
        uid = create_user(uname, generate_password_hash(uuid.uuid4().hex), email)
        user = get_user_by_email(email)
    session['user_id'] = user['id']
    session['username'] = user['username']
    from flask import redirect as flask_redirect
    return flask_redirect(f"{FRONTEND_URL}/dashboard?login=success")


# ─── GOOGLE DRIVE CONNECTION ───
@app.route("/api/drive/connect")
@login_required
def api_drive_connect():
    flow = Flow.from_client_config({
        "web": {
            "client_id": GOOGLE_OAUTH_CLIENT_ID,
            "client_secret": GOOGLE_OAUTH_CLIENT_SECRET,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [f"{BACKEND_URL}/api/drive/callback"]
        }
    }, scopes=SCOPES)
    flow.redirect_uri = f"{BACKEND_URL}/api/drive/callback"
    url, state = flow.authorization_url(access_type='offline', prompt='consent')
    session['drive_auth_state'] = state
    return jsonify({"auth_url": url})

@app.route("/api/drive/callback")
def api_drive_callback():
    uid = session.get('user_id')
    state = session.get('drive_auth_state')
    if not uid:
        from flask import redirect as flask_redirect
        return flask_redirect(f"{FRONTEND_URL}/login?error=session_expired")
    try:
        flow = Flow.from_client_config({
            "web": {
                "client_id": GOOGLE_OAUTH_CLIENT_ID,
                "client_secret": GOOGLE_OAUTH_CLIENT_SECRET,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [f"{BACKEND_URL}/api/drive/callback"]
            }
        }, scopes=SCOPES, state=state)
        flow.redirect_uri = f"{BACKEND_URL}/api/drive/callback"
        flow.fetch_token(authorization_response=request.url)
        creds = flow.credentials
        cd = {
            'token': creds.token,
            'refresh_token': creds.refresh_token,
            'token_uri': creds.token_uri,
            'client_id': creds.client_id,
            'client_secret': creds.client_secret,
            'scopes': list(creds.scopes) if creds.scopes else SCOPES
        }
        save_drive_credentials(uid, json.dumps(cd))
        from flask import redirect as flask_redirect
        return flask_redirect(f"{FRONTEND_URL}/dashboard?drive=connected")
    except Exception as e:
        logger.error(f"Drive callback error: {e}")
        from flask import redirect as flask_redirect
        return flask_redirect(f"{FRONTEND_URL}/dashboard?drive=error")

@app.route("/api/drive/disconnect", methods=["POST"])
@login_required
def api_drive_disconnect():
    uid = session['user_id']
    update_user_state(uid, google_drive_credentials=None, drive_connected=False, spreadsheet_id=None)
    return jsonify({"message": "Drive disconnected"})


# ─── UPLOAD & PREVIEW ───
@app.route("/api/upload/preview", methods=["POST"])
@login_required
def api_preview():
    uid = session['user_id']
    file = request.files.get("file")
    url_input = request.form.get("url", "").strip()
    text_input = request.form.get("text", "").strip()

    if file and file.filename:
        data = file.read()
        fn = file.filename
        sp = upload_to_supabase(uid, data, fn)
        if not sp:
            return jsonify({"error": "File upload failed"}), 500
        dl = download_from_supabase(sp)
        content = extract_text(dl, fn) if dl else "[extraction failed]"
        heading, desc = gemini.generate(content)
        return jsonify({
            "heading": heading, "description": desc,
            "source": "file", "supabase_path": sp,
            "filename": fn, "content_snippet": content[:500]
        })
    elif url_input:
        content = extract_from_url(url_input)
        heading, desc = gemini.generate(content)
        return jsonify({
            "heading": heading, "description": desc,
            "source": "url", "url": url_input,
            "content_snippet": content[:500]
        })
    elif text_input:
        heading, desc = gemini.generate(text_input)
        return jsonify({
            "heading": heading, "description": desc,
            "source": "text", "content_snippet": text_input[:500]
        })
    return jsonify({"error": "No content provided"}), 400


@app.route("/api/upload/save", methods=["POST"])
@login_required
def api_save():
    uid = session['user_id']
    data = request.get_json()
    heading = data.get("heading", "").strip()
    description = data.get("description", "").strip()
    source = data.get("source", "")
    url_val = data.get("url")
    supabase_path = data.get("supabase_path")
    filename = data.get("filename")

    if not heading:
        return jsonify({"error": "Title is required"}), 400

    # Try Drive upload if connected
    drive_link = None
    state = get_user_state(uid)
    dc = state and state.get('drive_connected') and get_drive_credentials(uid)
    if dc and source == "file" and supabase_path and filename:
        drive_link = upload_to_drive(uid, supabase_path, filename)

    try:
        insert_data = {
            'user_id': uid,
            'title': heading,
            'content': description,
            'source_type': source,
            'source_name': url_val or filename or "manual",
            'completed': False,
            'next_revision_date': date.today().isoformat(),
            'revision_count': 0,
        }
        if supabase_path:
            insert_data['supabase_path'] = supabase_path
        if drive_link:
            insert_data['drive_link'] = drive_link

        lr = supabase.table('learnings').insert(insert_data).execute()
        lid = lr.data[0]['id']

        if dc:
            try:
                append_to_sheet(uid, {
                    "heading": heading, "description": description,
                    "input_type": source, "source": source,
                    "drive_link": drive_link or "", "url": url_val or ""
                })
            except:
                pass

        schedule_revisions(uid, lid, heading, description, drive_link, url_val, supabase_path)

        return jsonify({
            "message": "Saved and scheduled!",
            "learning_id": lid,
            "drive_link": drive_link
        }), 201
    except Exception as e:
        logger.error(f"Save error: {e}")
        return jsonify({"error": str(e)}), 500


# ─── REVISIONS ───
@app.route("/api/revisions/today")
@login_required
def api_today():
    uid = session['user_id']
    today = date.today().isoformat()
    cleanup_old_files(uid)
    r = supabase.table('revisions').select('*').eq('user_id', uid).eq('scheduled_date', today).eq('completed', False).order('stage').execute()
    return jsonify([_build_revision(row) for row in r.data])

@app.route("/api/revisions/overdue")
@login_required
def api_overdue():
    uid = session['user_id']
    today = date.today().isoformat()
    r = supabase.table('revisions').select('*').eq('user_id', uid).lt('scheduled_date', today).eq('completed', False).order('scheduled_date').execute()
    return jsonify([_build_revision(row) for row in r.data])

@app.route("/api/revisions/completed")
@login_required
def api_completed():
    uid = session['user_id']
    today = date.today().isoformat()
    r = supabase.table('revisions').select('*').eq('user_id', uid).eq('completed_date', today).eq('completed', True).execute()
    return jsonify([_build_revision(row) for row in r.data])

@app.route("/api/revisions/upcoming")
@login_required
def api_upcoming():
    uid = session['user_id']
    tomorrow = (date.today() + timedelta(days=1)).isoformat()
    r = supabase.table('revisions').select('*').eq('user_id', uid).gte('scheduled_date', tomorrow).eq('completed', False).order('scheduled_date').execute()
    revisions = [_build_revision(row) for row in r.data]
    # Group by date
    grouped = {}
    for rev in revisions:
        d = rev['scheduled_date']
        grouped.setdefault(d, []).append(rev)
    return jsonify({"grouped": grouped, "total": len(revisions)})

@app.route("/api/revisions/stats")
@login_required
def api_stats():
    uid = session['user_id']
    stats = get_revision_stats(uid)
    streak, _ = get_user_streak(uid)
    stats['streak'] = streak
    return jsonify(stats)

@app.route("/api/revisions/<revision_id>/complete", methods=["POST"])
@login_required
def api_complete(revision_id):
    uid = session['user_id']
    r = supabase.table('revisions').select('learning_id', 'stage').eq('id', revision_id).eq('user_id', uid).execute()
    if not r.data:
        return jsonify({"error": "Not found"}), 404
    lid = r.data[0]['learning_id']
    stg = r.data[0]['stage']
    supabase.table('revisions').update({'completed': True, 'completed_date': date.today().isoformat()}).eq('id', revision_id).execute()
    supabase.table('learnings').update({'revision_stage': stg}).eq('id', lid).execute()
    update_streak(uid)
    return jsonify({"message": "Completed!"})

@app.route("/api/revisions/<revision_id>/postpone", methods=["POST"])
@login_required
def api_postpone(revision_id):
    uid = session['user_id']
    tomorrow = (date.today() + timedelta(days=1)).isoformat()
    supabase.table('revisions').update({'scheduled_date': tomorrow}).eq('id', revision_id).eq('user_id', uid).execute()
    return jsonify({"message": "Postponed to tomorrow"})

@app.route("/api/revisions/<revision_id>/skip", methods=["POST"])
@login_required
def api_skip(revision_id):
    """Skip a revision — reschedule to the next day"""
    uid = session['user_id']
    r = supabase.table('revisions').select('scheduled_date').eq('id', revision_id).eq('user_id', uid).execute()
    if not r.data:
        return jsonify({"error": "Not found"}), 404
    current = r.data[0]['scheduled_date']
    new_date = (datetime.strptime(current, "%Y-%m-%d").date() + timedelta(days=1)).isoformat()
    supabase.table('revisions').update({'scheduled_date': new_date}).eq('id', revision_id).execute()
    return jsonify({"message": f"Skipped to {new_date}"})


# ─── LEARNINGS HISTORY ───
@app.route("/api/learnings")
@login_required
def api_learnings():
    uid = session['user_id']
    r = supabase.table('learnings').select('*').eq('user_id', uid).order('created_at', desc=True).limit(50).execute()
    return jsonify(r.data)


# ─── DOWNLOAD ───
@app.route("/api/download/<path:supabase_path>")
@login_required
def api_download(supabase_path):
    uid = session['user_id']
    if not supabase_path.startswith(f"{uid}/"):
        return jsonify({"error": "Unauthorized"}), 403
    url = get_supabase_url(supabase_path)
    if url:
        return jsonify({"download_url": url})
    return jsonify({"error": "File not found"}), 404


# ─── HEALTH ───
@app.route("/api/health")
def health():
    return jsonify({"status": "ok", "timestamp": datetime.utcnow().isoformat()})


if __name__ == "__main__":
    ensure_bucket_exists()
    app.run(debug=True, host="0.0.0.0", port=5000)
