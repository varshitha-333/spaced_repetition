import os
import re
import time
from datetime import datetime, date, timedelta
from pathlib import Path
import requests
from bs4 import BeautifulSoup
from flask import Flask, request, jsonify, session, redirect as flask_redirect
from flask_cors import CORS
from werkzeug.middleware.proxy_fix import ProxyFix
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
import traceback
from tempfile import NamedTemporaryFile
import urllib.parse
import jwt as pyjwt   # pip install PyJWT
from zoneinfo import ZoneInfo
try:
    from twilio.rest import Client as TwilioClient
except Exception:
    TwilioClient = None

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

supabase: Client = None
if SUPABASE_URL and SUPABASE_KEY:
    try:
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        logger.info("✅ Supabase client initialised")
    except Exception as e:
        logger.error(f"❌ Supabase init failed: {e}")
else:
    logger.warning("⚠️  SUPABASE_URL / SUPABASE_KEY missing — backend in degraded mode")

GOOGLE_OAUTH_CLIENT_ID = os.getenv("GOOGLE_OAUTH_CLIENT_ID")
GOOGLE_OAUTH_CLIENT_SECRET = os.getenv("GOOGLE_OAUTH_CLIENT_SECRET")
BACKEND_URL  = os.getenv("BACKEND_URL",  "http://localhost:5000").rstrip("/")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173").rstrip("/")

GOOGLE_LOGIN_REDIRECT = f"{BACKEND_URL}/api/auth/google/callback"
GOOGLE_DRIVE_REDIRECT = f"{BACKEND_URL}/api/drive/callback"
logger.info("═══════════════════════════════════════════════════════")
logger.info(f"BACKEND_URL  = {BACKEND_URL}")
logger.info(f"FRONTEND_URL = {FRONTEND_URL}")
logger.info(f"Google login  redirect_uri = {GOOGLE_LOGIN_REDIRECT}")
logger.info(f"Google drive  redirect_uri = {GOOGLE_DRIVE_REDIRECT}")
logger.info("↑ These two URIs MUST be added EXACTLY to Google Cloud Console →")
logger.info("  APIs & Services → Credentials → OAuth 2.0 Client → Authorized redirect URIs")
logger.info("═══════════════════════════════════════════════════════")

APP_FOLDER_NAME = "Learning Intake"
SHEET_TITLE = "Learning Intake Log"
REVISION_INTERVALS = [1, 3, 6, 29, 179]

REVISION_STAGE_LABELS = [f"Day {days}" for days in REVISION_INTERVALS]
DEFAULT_NOTIFICATION_HOUR = int(os.getenv("DEFAULT_NOTIFICATION_HOUR", "8"))
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_FROM_PHONE = os.getenv("TWILIO_FROM_PHONE")
DAILY_NOTIFICATION_SECRET = os.getenv("DAILY_NOTIFICATION_SECRET")
APP_DEEP_LINK = f"{FRONTEND_URL}/today"
NOTIFICATION_QUOTES = [
    "Success is the sum of small efforts repeated day in and day out.",
    "A little progress each day adds up to big results.",
    "Discipline today creates confidence tomorrow.",
    "Your future self will thank you for the revision you do today.",
    "Consistency beats intensity when learning for the long run.",
    "Every review is a vote for the person you want to become.",
    "Tiny study wins compound into major breakthroughs.",
    "Stay patient — memory grows stronger with every recall.",
    "The best streak is the one you protect today.",
    "Keep showing up. That is how difficult things become familiar.",
]

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "change-this-to-a-strong-secret-in-production")

# ProxyFix so request.is_secure is correct behind Render's load balancer
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_port=1)

# Sessions are only used now for transient OAuth state (Google login + Drive connect).
# All protected-route auth is handled via JWT in the Authorization header.
app.config.update(
    SESSION_COOKIE_NAME='learnflow_session',
    SESSION_COOKIE_SAMESITE='None',
    SESSION_COOKIE_SECURE=True,
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_PERMANENT=False,          # short-lived — only needed for OAuth state round-trip
    PERMANENT_SESSION_LIFETIME=timedelta(minutes=10),
)

@app.before_request
def _make_session_permanent():
    session.permanent = True

# ════════════════════════════════════════════════════════════════
# CORS
# ════════════════════════════════════════════════════════════════
ALLOWED_ORIGINS = [
    FRONTEND_URL,
    "http://localhost:5173",
    "http://localhost:3000",
    "https://spaced-repetition-umber.vercel.app",
]
VERCEL_PREVIEW_REGEX = re.compile(r"^https://.*\.vercel\.app$")

CORS(
    app,
    supports_credentials=True,
    origins=ALLOWED_ORIGINS + [VERCEL_PREVIEW_REGEX],
    allow_headers=["Content-Type", "Authorization", "X-Requested-With"],
    methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    expose_headers=["Content-Type"],
    max_age=600,
)

DEBUG_AUTH = os.getenv("DEBUG_AUTH", "1") == "1"

@app.before_request
def _debug_log_request():
    if not DEBUG_AUTH:
        return
    if request.path.startswith("/api/"):
        auth = request.headers.get('Authorization', '')
        has_jwt = auth.startswith('Bearer ')
        logger.info(
            f"[REQ] {request.method} {request.path} "
            f"origin={request.headers.get('Origin')} "
            f"has_jwt={has_jwt}"
        )

@app.after_request
def _debug_log_response(resp):
    if DEBUG_AUTH and request.path.startswith("/api/"):
        logger.info(f"[RESP] {request.method} {request.path} → {resp.status_code}")
    return resp


# ═══════════════════════════════════════════════════════
#  ROOT + HEALTH ROUTES
# ═══════════════════════════════════════════════════════
@app.route("/")
def root():
    return jsonify({
        "service": "LearnFlow Backend",
        "status": "running",
        "version": "2.0-jwt-auth",
        "supabase": "connected" if supabase else "not_configured",
        "endpoints": ["/api/auth/register", "/api/auth/login", "/api/auth/me", "/api/health"]
    })

@app.route("/health")
def health_root():
    return jsonify({"status": "ok"})

@app.route("/api/health")
def api_health():
    return jsonify({
        "status": "ok",
        "timestamp": datetime.utcnow().isoformat(),
        "supabase": bool(supabase),
        "frontend_url": FRONTEND_URL,
        "backend_url": BACKEND_URL,
        "auth_method": "JWT",
    })

@app.route("/privacy")
def privacy():
    return jsonify({"privacy": "Privacy Policy"})


# ─── BUCKET SETUP ───
def ensure_bucket_exists():
    if not supabase:
        return False
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


# ════════════════════════════════════════════════════════════════
#  JWT HELPERS
# ════════════════════════════════════════════════════════════════
JWT_ALGORITHM = "HS256"
JWT_EXPIRY_DAYS = 30

def make_token(user_id: str, username: str) -> str:
    """Create a signed JWT valid for JWT_EXPIRY_DAYS days."""
    payload = {
        "user_id": user_id,
        "username": username,
        "exp": datetime.utcnow() + timedelta(days=JWT_EXPIRY_DAYS),
        "iat": datetime.utcnow(),
    }
    return pyjwt.encode(payload, app.secret_key, algorithm=JWT_ALGORITHM)


def decode_token(token: str) -> dict:
    """Decode and validate a JWT. Raises pyjwt.InvalidTokenError on failure."""
    return pyjwt.decode(token, app.secret_key, algorithms=[JWT_ALGORITHM])


# ════════════════════════════════════════════════════════════════
#  OAUTH STATE HELPERS  (cross-domain safe — no cookies needed)
# ════════════════════════════════════════════════════════════════
import base64

def encode_state(data: dict) -> str:
    """Encode arbitrary dict into a URL-safe base64 string for the OAuth state param."""
    return base64.urlsafe_b64encode(json.dumps(data).encode()).decode()

def decode_state(state: str) -> dict:
    """Decode the OAuth state param back to a dict. Returns {} on any error."""
    try:
        return json.loads(base64.urlsafe_b64decode(state.encode()).decode())
    except Exception:
        return {}


# ─── AUTH HELPERS ───
def login_required(f):
    """
    Protect a route with JWT.
    Reads the token from the Authorization: Bearer <token> header.
    Sets request.user_id and request.username for use inside the view.
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get("Authorization", "")
        token = auth_header.removeprefix("Bearer ").strip()
        if not token:
            if DEBUG_AUTH:
                logger.warning(
                    f"[AUTH-FAIL] {request.method} {request.path} — "
                    f"no Authorization header. origin={request.headers.get('Origin')}"
                )
            return jsonify({"error": "Authentication required"}), 401
        try:
            data = decode_token(token)
            request.user_id = data["user_id"]
            request.username = data.get("username", "")
        except pyjwt.ExpiredSignatureError:
            return jsonify({"error": "Session expired — please log in again"}), 401
        except pyjwt.InvalidTokenError as e:
            logger.warning(f"[AUTH-FAIL] Invalid JWT: {e}")
            return jsonify({"error": "Invalid token"}), 401
        return f(*args, **kwargs)
    return decorated


# ─── DATABASE HELPERS ───
def get_user_by_username(username):
    if not supabase:
        return None
    try:
        r = supabase.table('users').select('*').eq('username', username).execute()
        return r.data[0] if r.data else None
    except Exception as e:
        logger.error(f"get_user_by_username error: {e}")
        return None

def get_user_by_email(email):
    if not supabase:
        return None
    try:
        r = supabase.table('users').select('*').eq('email', email).execute()
        return r.data[0] if r.data else None
    except Exception as e:
        logger.error(f"get_user_by_email error: {e}")
        return None


def get_user_by_id(user_id):
    if not supabase:
        return None
    try:
        r = supabase.table('users').select('*').eq('id', user_id).execute()
        return r.data[0] if r.data else None
    except Exception as e:
        logger.error(f"get_user_by_id error: {e}")
        return None

def create_user(username, password_hash, email):
    """Returns (user_id, error_message). user_id is None on failure."""
    if not supabase:
        return None, "Database not configured (SUPABASE_URL/SUPABASE_KEY missing)"
    try:
        r = supabase.table('users').insert({
            'username': username,
            'password_hash': password_hash,
            'email': email
        }).execute()
        if not r.data:
            return None, "Insert returned no rows (check RLS policies on 'users' table)"
        uid = r.data[0]['id']
        try:
            supabase.table('user_state').insert({
                'user_id': uid,
                'drive_connected': False,
                'spreadsheet_id': None,
                'current_streak': 0,
                'last_completion_date': None,
                'google_drive_credentials': None,
                'notification_phone': None,
                'sms_notifications_enabled': False,
                'notification_timezone': 'UTC',
                'notification_hour': DEFAULT_NOTIFICATION_HOUR,
                'last_sms_sent_date': None
            }).execute()
        except Exception as e:
            logger.warning(f"user_state insert failed (non-fatal): {e}")
        return uid, None
    except Exception as e:
        err = f"{type(e).__name__}: {str(e)}"
        logger.error(f"Create user error: {err}\n{traceback.format_exc()}")
        return None, err

def get_user_state(user_id):
    if not supabase: return None
    try:
        r = supabase.table('user_state').select('*').eq('user_id', user_id).execute()
        return r.data[0] if r.data else None
    except:
        return None

def update_user_state(user_id, **kwargs):
    if not supabase: return False
    try:
        supabase.table('user_state').update(kwargs).eq('user_id', user_id).execute()
        return True
    except:
        return False

def save_drive_credentials(user_id, creds_json):
    if not supabase: return False
    try:
        supabase.table('user_state').update({
            'google_drive_credentials': creds_json,
            'drive_connected': True
        }).eq('user_id', user_id).execute()
        return True
    except:
        return False

def get_drive_credentials(user_id):
    if not supabase: return None
    try:
        r = supabase.table('user_state').select('google_drive_credentials').eq('user_id', user_id).execute()
        if r.data and r.data[0]['google_drive_credentials']:
            return r.data[0]['google_drive_credentials']
        return None
    except:
        return None


def is_twilio_configured():
    return bool(TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN and TWILIO_FROM_PHONE and TwilioClient)


def normalize_phone_number(raw_phone):
    if not raw_phone:
        return None
    cleaned = re.sub(r"[^\d+]", "", str(raw_phone).strip())
    if cleaned.startswith("00"):
        cleaned = "+" + cleaned[2:]
    if cleaned and not cleaned.startswith("+"):
        cleaned = "+" + cleaned
    if not re.fullmatch(r"\+\d{8,15}", cleaned or ""):
        raise ValueError("Phone number must be in international format, for example +14155550100")
    return cleaned


def resolve_user_timezone(tz_name):
    try:
        return ZoneInfo(tz_name or "UTC")
    except Exception:
        return ZoneInfo("UTC")


def get_quote_for_date(target_date):
    if not NOTIFICATION_QUOTES:
        return "Keep going — every review strengthens your memory."
    return NOTIFICATION_QUOTES[target_date.toordinal() % len(NOTIFICATION_QUOTES)]


def get_revision_link(row):
    if row.get('drive_link'):
        return row.get('drive_link')
    if row.get('url'):
        return row.get('url')
    if row.get('supabase_path'):
        return get_supabase_url(row.get('supabase_path'))
    return None


def get_due_revision_buckets(user_id, target_day):
    if not supabase:
        return [], []
    day_str = target_day.isoformat()
    today_rows = supabase.table('revisions').select('*').eq('user_id', user_id).eq('scheduled_date', day_str).eq('completed', False).order('stage').execute().data or []
    overdue_rows = supabase.table('revisions').select('*').eq('user_id', user_id).lt('scheduled_date', day_str).eq('completed', False).order('scheduled_date').execute().data or []
    return today_rows, overdue_rows


def build_daily_sms(username, target_day, today_rows, overdue_rows, streak):
    pretty_date = target_day.strftime("%A, %b %d")
    today_lines = []
    for idx, row in enumerate(today_rows, start=1):
        label = REVISION_STAGE_LABELS[(row.get('stage', 1) - 1)] if row.get('stage') else f"Stage {idx}"
        title = row.get('heading', 'Untitled')
        link = get_revision_link(row)
        line = f"{idx}. {title} ({label})"
        if link:
            line += f" - {link}"
        today_lines.append(line)

    carry_forward = []
    for row in overdue_rows[:5]:
        carry_forward.append(row.get('heading', 'Untitled'))

    lines = [
        f"Good morning {username}! ☀️",
        f"Today's LearnFlow revision plan for {pretty_date}: {len(today_rows)} due now, {len(overdue_rows)} carried forward, streak {streak} day(s).",
        "Complete today's reviews to protect your momentum.",
    ]

    if today_lines:
        lines.append("Today's revision links:")
        lines.extend(today_lines)
    else:
        lines.append("No new revisions are due today, but check your carry-forward items below.")

    if carry_forward:
        suffix = "" if len(overdue_rows) <= 5 else f" +{len(overdue_rows) - 5} more"
        lines.append(f"Due from previous day(s): {', '.join(carry_forward)}{suffix}")

    lines.append(f"Motivation: {get_quote_for_date(target_day)}")
    lines.append(f"Open LearnFlow: {APP_DEEP_LINK}")
    return "\n".join(lines)


def send_sms_message(phone_number, body):
    if not is_twilio_configured():
        raise RuntimeError("Twilio is not configured")
    client = TwilioClient(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
    return client.messages.create(
        body=body,
        from_=TWILIO_FROM_PHONE,
        to=phone_number,
    )


def sync_learning_progress(user_id, learning_id):
    if not supabase or not learning_id:
        return
    try:
        pending = supabase.table('revisions').select('stage, scheduled_date').eq('user_id', user_id).eq('learning_id', learning_id).eq('completed', False).order('scheduled_date').limit(1).execute()
        if pending.data:
            next_row = pending.data[0]
            supabase.table('learnings').update({
                'revision_stage': max((next_row.get('stage') or 1) - 1, 0),
                'next_revision_date': next_row.get('scheduled_date')
            }).eq('id', learning_id).execute()
        else:
            supabase.table('learnings').update({
                'revision_stage': len(REVISION_INTERVALS),
                'next_revision_date': None,
                'completed': True
            }).eq('id', learning_id).execute()
    except Exception as e:
        logger.warning(f"sync_learning_progress failed for {learning_id}: {e}")



# ─── SUPABASE STORAGE ───
def sanitize_filename(filename):
    safe = secure_filename(filename)
    safe = safe.replace('%', '_').replace('#', '_').replace('&', '_')
    name, ext = os.path.splitext(safe)
    return f"{name[:100]}{ext}"

def upload_to_supabase(user_id, file_data, filename):
    if not supabase: return None
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
    if not supabase: return None
    try:
        return supabase.storage.from_(SUPABASE_BUCKET).download(path)
    except:
        return None

def get_supabase_url(path):
    if not supabase: return None
    try:
        r = supabase.storage.from_(SUPABASE_BUCKET).create_signed_url(path, expires_in=3600)
        return r.get('signedURL')
    except:
        return None

def cleanup_old_files(user_id):
    if not supabase: return
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
    if not supabase: return 0
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
    if not supabase: return False
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


def get_due_logic_summary():
    return {
        "intervals": REVISION_INTERVALS,
        "labels": REVISION_STAGE_LABELS,
        "description": "Every new learning item is scheduled for review on Day 1, 3, 6, 29 and 179. Missed reviews remain overdue until completed, so weaker memories keep resurfacing."
    }

def get_revision_stats(user_id):
    if not supabase:
        return {"today": 0, "overdue": 0, "completed_today": 0, "tomorrow": 0, "future": 0}
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
    try:
        data = request.get_json(force=True, silent=True) or {}
        username = data.get("username", "").strip()
        password = data.get("password", "").strip()
        email = data.get("email", "").strip()

        if not username or not password or not email:
            return jsonify({"error": "All fields required"}), 400
        if len(password) < 6:
            return jsonify({"error": "Password must be at least 6 characters"}), 400
        if not supabase:
            return jsonify({"error": "Backend database not configured. Contact administrator."}), 503
        if get_user_by_username(username):
            return jsonify({"error": "Username already exists"}), 400
        if get_user_by_email(email):
            return jsonify({"error": "Email already registered"}), 400

        uid, err = create_user(username, generate_password_hash(password), email)
        if uid:
            token = make_token(uid, username)
            logger.info(f"[REGISTER OK] user_id={uid} username={username}")
            return jsonify({
                "message": "Registration successful",
                "token": token,
                "user": {"id": uid, "username": username, "email": email}
            }), 201
        return jsonify({"error": f"Registration failed: {err or 'unknown'}"}), 500
    except Exception as e:
        logger.error(f"Register endpoint crashed: {e}\n{traceback.format_exc()}")
        return jsonify({"error": f"Server error: {str(e)}"}), 500


@app.route("/api/auth/login", methods=["POST"])
def api_login():
    try:
        data = request.get_json(force=True, silent=True) or {}
        username = data.get("username", "").strip()
        password = data.get("password", "").strip()
        if not username or not password:
            return jsonify({"error": "Credentials required"}), 400
        if not supabase:
            return jsonify({"error": "Backend database not configured"}), 503
        user = get_user_by_username(username)
        if user and user.get('password_hash') and check_password_hash(user['password_hash'], password):
            token = make_token(user['id'], username)
            logger.info(f"[LOGIN OK] user_id={user['id']} username={username}")
            return jsonify({
                "message": "Login successful",
                "token": token,
                "user": {"id": user['id'], "username": username, "email": user.get('email')}
            })
        logger.warning(f"[LOGIN FAIL] username={username} - invalid credentials")
        return jsonify({"error": "Invalid credentials"}), 401
    except Exception as e:
        logger.error(f"Login error: {e}\n{traceback.format_exc()}")
        return jsonify({"error": f"Server error: {str(e)}"}), 500


@app.route("/api/auth/logout", methods=["POST"])
def api_logout():
    # With JWT the client discards the token; nothing to do server-side.
    logger.info("[LOGOUT] JWT logout — client should delete token")
    return jsonify({"message": "Logged out"})


@app.route("/api/auth/me")
def api_me():
    auth_header = request.headers.get("Authorization", "")
    token = auth_header.removeprefix("Bearer ").strip()
    if not token:
        return jsonify({"user": None}), 401
    try:
        data = decode_token(token)
        user_id = data["user_id"]
        username = data.get("username", "")
        state = get_user_state(user_id) or {}
        dc = False
        if state.get('drive_connected'):
            cj = get_drive_credentials(user_id)
            dc = cj is not None
        logger.info(f"[ME OK] user_id={user_id}")
        return jsonify({
            "user": {
                "id": user_id,
                "username": username,
                "drive_connected": dc,
                "drive_status": "connected" if dc else "not_connected",
                "notification_phone": state.get('notification_phone'),
                "sms_notifications_enabled": bool(state.get('sms_notifications_enabled')),
                "notification_timezone": state.get('notification_timezone') or "UTC",
                "notification_hour": state.get('notification_hour', DEFAULT_NOTIFICATION_HOUR),
                "twilio_configured": is_twilio_configured(),
            }
        })
    except pyjwt.ExpiredSignatureError:
        return jsonify({"user": None}), 401
    except pyjwt.InvalidTokenError:
        return jsonify({"user": None}), 401


@app.route("/api/notifications/preferences", methods=["GET", "PUT"])
@login_required
def api_notification_preferences():
    uid = request.user_id
    state = get_user_state(uid) or {}

    if request.method == "GET":
        return jsonify({
            "phone_number": state.get('notification_phone'),
            "enabled": bool(state.get('sms_notifications_enabled')),
            "timezone": state.get('notification_timezone') or "UTC",
            "notification_hour": state.get('notification_hour', DEFAULT_NOTIFICATION_HOUR),
            "twilio_configured": is_twilio_configured(),
        })

    data = request.get_json(force=True, silent=True) or {}
    enabled = bool(data.get('enabled'))
    timezone_name = (data.get('timezone') or state.get('notification_timezone') or 'UTC').strip()
    notification_hour = int(data.get('notification_hour', state.get('notification_hour', DEFAULT_NOTIFICATION_HOUR)))
    current_phone = state.get('notification_phone')
    raw_phone = (data.get('phone_number') or current_phone or '').strip()

    try:
        ZoneInfo(timezone_name)
    except Exception:
        return jsonify({"error": "Invalid timezone"}), 400

    if notification_hour < 0 or notification_hour > 23:
        return jsonify({"error": "notification_hour must be between 0 and 23"}), 400

    normalized_phone = None
    if raw_phone:
        try:
            normalized_phone = normalize_phone_number(raw_phone)
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400

    if enabled and not normalized_phone:
        return jsonify({"error": "Phone number is required to enable SMS reminders"}), 400

    updates = {
        'notification_phone': normalized_phone,
        'sms_notifications_enabled': enabled,
        'notification_timezone': timezone_name,
        'notification_hour': notification_hour,
    }
    if not update_user_state(uid, **updates):
        return jsonify({"error": "Could not save notification preferences. Ensure the new columns exist in user_state."}), 500

    return jsonify({
        "message": "Notification preferences saved",
        "preferences": {
            "phone_number": normalized_phone,
            "enabled": enabled,
            "timezone": timezone_name,
            "notification_hour": notification_hour,
            "twilio_configured": is_twilio_configured(),
        }
    })


@app.route("/api/notifications/send-daily", methods=["POST"])
def api_send_daily_notifications():
    provided_secret = request.headers.get("X-Notification-Secret", "")
    if not DAILY_NOTIFICATION_SECRET or provided_secret != DAILY_NOTIFICATION_SECRET:
        return jsonify({"error": "Unauthorized"}), 403
    if not supabase:
        return jsonify({"error": "Database not configured"}), 503
    if not is_twilio_configured():
        return jsonify({"error": "Twilio is not configured"}), 503

    processed = []
    skipped = []
    states = supabase.table('user_state').select('*').execute().data or []

    for state in states:
        if not state.get('sms_notifications_enabled') or not state.get('notification_phone'):
            continue

        user_id = state.get('user_id')
        user = get_user_by_id(user_id)
        if not user:
            skipped.append({"user_id": user_id, "reason": "user_not_found"})
            continue

        zone = resolve_user_timezone(state.get('notification_timezone'))
        local_now = datetime.now(zone)
        local_today = local_now.date()
        target_hour = int(state.get('notification_hour') or DEFAULT_NOTIFICATION_HOUR)

        if local_now.hour != target_hour:
            skipped.append({"user_id": user_id, "reason": "outside_delivery_hour", "timezone": str(zone), "local_hour": local_now.hour})
            continue

        if state.get('last_sms_sent_date') == local_today.isoformat():
            skipped.append({"user_id": user_id, "reason": "already_sent_today"})
            continue

        today_rows, overdue_rows = get_due_revision_buckets(user_id, local_today)
        if not today_rows and not overdue_rows:
            skipped.append({"user_id": user_id, "reason": "nothing_due"})
            continue

        streak, _ = get_user_streak(user_id)
        body = build_daily_sms(user.get('username', 'Learner'), local_today, today_rows, overdue_rows, streak)
        try:
            result = send_sms_message(state['notification_phone'], body)
            update_user_state(user_id, last_sms_sent_date=local_today.isoformat())
            processed.append({
                "user_id": user_id,
                "username": user.get('username'),
                "phone_number": state['notification_phone'],
                "twilio_sid": getattr(result, 'sid', None),
                "due_today": len(today_rows),
                "overdue": len(overdue_rows),
            })
        except Exception as exc:
            logger.error(f"Daily SMS failed for {user_id}: {exc}")
            skipped.append({"user_id": user_id, "reason": f"send_failed: {exc}"})

    return jsonify({
        "message": "Daily notification job completed",
        "sent": processed,
        "skipped": skipped,
        "processed_count": len(processed),
    })


# ─── GOOGLE AUTH (Sign in with Google) ───
@app.route("/api/auth/google")
def api_google_auth():
    if not GOOGLE_OAUTH_CLIENT_ID or not GOOGLE_OAUTH_CLIENT_SECRET:
        return jsonify({"error": "Google OAuth not configured"}), 503
    mode = request.args.get("mode", "login")   # "login" or "register"
    flow = Flow.from_client_config({
        "web": {
            "client_id": GOOGLE_OAUTH_CLIENT_ID,
            "client_secret": GOOGLE_OAUTH_CLIENT_SECRET,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [GOOGLE_LOGIN_REDIRECT]
        }
    }, scopes=["openid", "https://www.googleapis.com/auth/userinfo.email", "https://www.googleapis.com/auth/userinfo.profile"])
    flow.redirect_uri = GOOGLE_LOGIN_REDIRECT
    logger.info(f"[Google login] Sending redirect_uri to Google: {GOOGLE_LOGIN_REDIRECT}")

    # ── Encode mode into the state param so it survives the cross-domain redirect.
    # Session cookies are NOT sent by the browser when Google redirects back to a
    # different domain (Render backend vs Vercel frontend), so we can't rely on
    # session["google_auth_mode"]. The state param IS echoed back by Google in
    # the callback URL, making it a reliable cross-domain carrier. ──
    state_payload = encode_state({"mode": mode})
    url, _ = flow.authorization_url(access_type="offline", prompt="consent", state=state_payload)

    # Also keep in session as a belt-and-suspenders fallback for same-domain dev
    session["google_auth_state"] = state_payload
    session["google_auth_mode"] = mode
    session.permanent = True
    return jsonify({"auth_url": url})


@app.route("/api/auth/google/callback")
def api_google_callback():
    # ── Recover state from the URL param (cross-domain safe) first, then session. ──
    raw_state = request.args.get("state", "")
    state_data = decode_state(raw_state)
    # mode: "login" means only existing users are allowed;
    #        "register" (or anything else) auto-creates the account.
    mode = state_data.get("mode") or session.get("google_auth_mode", "login")

    session_state = session.get("google_auth_state")
    logger.info(f"[Google callback] session_state_present={session_state is not None} mode={mode}")
    # Use whichever state we have — the URL param carries our encoded payload so it
    # always wins; fall back to session for same-domain dev setups.
    final_state = raw_state or session_state
    logger.info(f"[Google callback] state taken from URL param: {raw_state is not None}")
    try:
        flow_kwargs = {"state": final_state} if final_state else {}
        flow = Flow.from_client_config({
            "web": {
                "client_id": GOOGLE_OAUTH_CLIENT_ID,
                "client_secret": GOOGLE_OAUTH_CLIENT_SECRET,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [GOOGLE_LOGIN_REDIRECT]
            }
        }, scopes=["openid", "https://www.googleapis.com/auth/userinfo.email", "https://www.googleapis.com/auth/userinfo.profile"], **flow_kwargs)
        flow.redirect_uri = GOOGLE_LOGIN_REDIRECT
        flow.fetch_token(authorization_response=request.url)
        creds = flow.credentials
        info = requests.get('https://www.googleapis.com/oauth2/v3/userinfo',
                            headers={'Authorization': f'Bearer {creds.token}'}).json()
        email = info.get('email')
        if not email:
            return flask_redirect(f"{FRONTEND_URL}/login?error=google_no_email")

        user = get_user_by_email(email)

        if not user:
            if mode == "login":
                # ── Only registered users may sign in with Google.
                # A user who hasn't registered yet must go through /register first. ──
                logger.warning(f"[Google login] email={email} not registered — blocking (mode=login)")
                return flask_redirect(f"{FRONTEND_URL}/login?error=google_not_registered")
            else:
                # mode == "register" — create the account automatically
                uname = email.split('@')[0] + '_' + uuid.uuid4().hex[:6]
                uid, err = create_user(uname, generate_password_hash(uuid.uuid4().hex), email)
                if not uid:
                    return flask_redirect(f"{FRONTEND_URL}/register?error=signup_failed")
                user = get_user_by_email(email)

        # ── Pass a JWT in the redirect URL instead of relying on cookies ──
        token = make_token(user['id'], user['username'])
        logger.info(f"[Google login OK] user_id={user['id']} email={email} — redirecting with JWT")
        return flask_redirect(f"{FRONTEND_URL}/dashboard?token={token}")
    except Exception as e:
        logger.error(f"Google callback error: {e}\n{traceback.format_exc()}")
        return flask_redirect(f"{FRONTEND_URL}/login?error=google_failed")


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
            "redirect_uris": [GOOGLE_DRIVE_REDIRECT]
        }
    }, scopes=SCOPES)
    flow.redirect_uri = GOOGLE_DRIVE_REDIRECT

    # ── Encode user_id into state so the drive callback can identify the user
    # even when the session cookie is lost across domains (Vercel ↔ Render). ──
    state_payload = encode_state({"user_id": request.user_id})
    url, _ = flow.authorization_url(access_type='offline', prompt='consent', state=state_payload)

    # Keep in session as belt-and-suspenders for same-domain dev setups
    session['drive_auth_state'] = state_payload
    session['drive_user_id'] = request.user_id
    return jsonify({"auth_url": url})

@app.route("/api/drive/callback")
def api_drive_callback():
    # ── PRIMARY: recover user_id from the state param (cross-domain safe).
    # The session cookie that stored drive_user_id during /api/drive/connect is
    # NOT sent back when Google redirects to the backend on a different domain
    # (Render) from the frontend (Vercel). The state param IS echoed back in
    # the callback URL by Google, so we decode user_id from it instead. ──
    raw_state = request.args.get("state", "")
    state_data = decode_state(raw_state)
    uid = (
        state_data.get("user_id")          # ← cross-domain safe (URL param)
        or session.get('drive_user_id')    # ← same-domain dev fallback
        or session.get('user_id')
    )
    logger.info(f"[Drive callback] uid={uid} state_data={state_data}")
    if not uid:
        logger.error("[Drive callback] No user_id — session cookie was lost cross-domain")
        return flask_redirect(f"{FRONTEND_URL}/dashboard?drive=error&reason=session_lost")
    try:
        flow = Flow.from_client_config({
            "web": {
                "client_id": GOOGLE_OAUTH_CLIENT_ID,
                "client_secret": GOOGLE_OAUTH_CLIENT_SECRET,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [GOOGLE_DRIVE_REDIRECT]
            }
        }, scopes=SCOPES, state=raw_state or None)
        flow.redirect_uri = GOOGLE_DRIVE_REDIRECT
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
        logger.info(f"[Drive callback] Drive connected for user_id={uid}")
        return flask_redirect(f"{FRONTEND_URL}/dashboard?drive=connected")
    except Exception as e:
        logger.error(f"Drive callback error: {e}")
        return flask_redirect(f"{FRONTEND_URL}/dashboard?drive=error")

@app.route("/api/drive/disconnect", methods=["POST"])
@login_required
def api_drive_disconnect():
    uid = request.user_id
    update_user_state(uid, google_drive_credentials=None, drive_connected=False, spreadsheet_id=None)
    return jsonify({"message": "Drive disconnected"})


# ─── UPLOAD & PREVIEW ───
@app.route("/api/upload/preview", methods=["POST"])
@login_required
def api_preview():
    uid = request.user_id
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
    uid = request.user_id
    data = request.get_json()
    heading = data.get("heading", "").strip()
    description = data.get("description", "").strip()
    source = data.get("source", "")
    url_val = data.get("url")
    supabase_path = data.get("supabase_path")
    filename = data.get("filename")

    if not heading:
        return jsonify({"error": "Title is required"}), 400

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
    uid = request.user_id
    today = date.today().isoformat()
    cleanup_old_files(uid)
    r = supabase.table('revisions').select('*').eq('user_id', uid).eq('scheduled_date', today).eq('completed', False).order('stage').execute()
    return jsonify([_build_revision(row) for row in r.data])

@app.route("/api/revisions/overdue")
@login_required
def api_overdue():
    uid = request.user_id
    today = date.today().isoformat()
    r = supabase.table('revisions').select('*').eq('user_id', uid).lt('scheduled_date', today).eq('completed', False).order('scheduled_date').execute()
    return jsonify([_build_revision(row) for row in r.data])

@app.route("/api/revisions/completed")
@login_required
def api_completed():
    uid = request.user_id
    today = date.today().isoformat()
    r = supabase.table('revisions').select('*').eq('user_id', uid).eq('completed_date', today).eq('completed', True).execute()
    return jsonify([_build_revision(row) for row in r.data])

@app.route("/api/revisions/upcoming")
@login_required
def api_upcoming():
    uid = request.user_id
    tomorrow = (date.today() + timedelta(days=1)).isoformat()
    r = supabase.table('revisions').select('*').eq('user_id', uid).gte('scheduled_date', tomorrow).eq('completed', False).order('scheduled_date').execute()
    revisions = [_build_revision(row) for row in r.data]
    grouped = {}
    for rev in revisions:
        d = rev['scheduled_date']
        grouped.setdefault(d, []).append(rev)
    return jsonify({"grouped": grouped, "total": len(revisions)})

@app.route("/api/revisions/stats")
@login_required
def api_stats():
    uid = request.user_id
    stats = get_revision_stats(uid)
    streak, _ = get_user_streak(uid)
    stats['streak'] = streak
    stats['due_logic'] = get_due_logic_summary()
    return jsonify(stats)

@app.route("/api/revisions/<revision_id>/complete", methods=["POST"])
@login_required
def api_complete(revision_id):
    uid = request.user_id
    r = supabase.table('revisions').select('learning_id', 'stage').eq('id', revision_id).eq('user_id', uid).execute()
    if not r.data:
        return jsonify({"error": "Not found"}), 404
    lid = r.data[0]['learning_id']
    stg = r.data[0]['stage']
    supabase.table('revisions').update({'completed': True, 'completed_date': date.today().isoformat()}).eq('id', revision_id).execute()
    supabase.table('learnings').update({'revision_stage': stg}).eq('id', lid).execute()
    sync_learning_progress(uid, lid)
    update_streak(uid)
    return jsonify({"message": "Completed!"})

@app.route("/api/revisions/<revision_id>/postpone", methods=["POST"])
@login_required
def api_postpone(revision_id):
    uid = request.user_id
    tomorrow = (date.today() + timedelta(days=1)).isoformat()
    r = supabase.table('revisions').select('learning_id').eq('id', revision_id).eq('user_id', uid).execute()
    if not r.data:
        return jsonify({"error": "Not found"}), 404
    lid = r.data[0]['learning_id']
    supabase.table('revisions').update({'scheduled_date': tomorrow}).eq('id', revision_id).eq('user_id', uid).execute()
    sync_learning_progress(uid, lid)
    return jsonify({"message": "Postponed to tomorrow"})

@app.route("/api/revisions/<revision_id>/skip", methods=["POST"])
@login_required
def api_skip(revision_id):
    uid = request.user_id
    r = supabase.table('revisions').select('scheduled_date', 'learning_id').eq('id', revision_id).eq('user_id', uid).execute()
    if not r.data:
        return jsonify({"error": "Not found"}), 404
    current = r.data[0]['scheduled_date']
    lid = r.data[0]['learning_id']
    new_date = (datetime.strptime(current, "%Y-%m-%d").date() + timedelta(days=1)).isoformat()
    supabase.table('revisions').update({'scheduled_date': new_date}).eq('id', revision_id).execute()
    sync_learning_progress(uid, lid)
    return jsonify({"message": f"Skipped to {new_date}"})


# ─── LEARNINGS HISTORY ───
@app.route("/api/learnings")
@login_required
def api_learnings():
    uid = request.user_id
    r = supabase.table('learnings').select('*').eq('user_id', uid).order('created_at', desc=True).limit(50).execute()
    return jsonify(r.data)


# ─── DOWNLOAD ───
@app.route("/api/download/<path:supabase_path>")
@login_required
def api_download(supabase_path):
    uid = request.user_id
    if not supabase_path.startswith(f"{uid}/"):
        return jsonify({"error": "Unauthorized"}), 403
    url = get_supabase_url(supabase_path)
    if url:
        return jsonify({"download_url": url})
    return jsonify({"error": "File not found"}), 404


if __name__ == "__main__":
    if supabase:
        ensure_bucket_exists()
    port = int(os.getenv("PORT", 5000))
    app.run(debug=True, host="0.0.0.0", port=port)