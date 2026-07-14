import os
import re
import time
from datetime import datetime, date, timedelta
from pathlib import Path
import requests
from bs4 import BeautifulSoup
from flask import Flask, request, jsonify, session, redirect as flask_redirect
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from werkzeug.middleware.proxy_fix import ProxyFix
from PyPDF2 import PdfReader
from docx import Document
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
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

# ─── ENVIRONMENT VALIDATION ───
def validate_environment():
    """Validate required environment variables at startup."""
    required_vars = {
        'SUPABASE_URL': os.getenv("SUPABASE_URL"),
        'SUPABASE_KEY': os.getenv("SUPABASE_KEY"),
        'FLASK_SECRET_KEY': os.getenv("FLASK_SECRET_KEY"),
    }
    
    missing = [k for k, v in required_vars.items() if not v]
    
    if missing:
        logger.error(f"❌ CRITICAL: Missing required environment variables: {', '.join(missing)}")
        logger.error("Please set these in your .env file or Render environment variables.")
        logger.error("See backend/.env.example for the required format.")
    
    optional_vars = {
        'GOOGLE_OAUTH_CLIENT_ID': os.getenv("GOOGLE_OAUTH_CLIENT_ID"),
        'GOOGLE_OAUTH_CLIENT_SECRET': os.getenv("GOOGLE_OAUTH_CLIENT_SECRET"),
        'GEMINI_API_KEY': os.getenv("GEMINI_API_KEY"),
        'TWILIO_ACCOUNT_SID': os.getenv("TWILIO_ACCOUNT_SID"),
        'TWILIO_AUTH_TOKEN': os.getenv("TWILIO_AUTH_TOKEN"),
        'TWILIO_FROM_PHONE': os.getenv("TWILIO_FROM_PHONE"),
    }
    
    optional_missing = [k for k, v in optional_vars.items() if not v]
    if optional_missing:
        logger.warning(f"⚠️  Optional services not configured: {', '.join(optional_missing)}")
        logger.warning("These features will be unavailable: Google OAuth, Gemini AI, Twilio SMS")
    
    return len(missing) == 0

# Validate environment on import
_env_valid = validate_environment()

# ─── RATE LIMITING ───
limiter = Limiter(
    get_remote_address,
    app=None,  # Will be set after app creation
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://",
)

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
        logger.error(f"Supabase URL: {SUPABASE_URL[:20]}... (truncated)")
        logger.error(f"Supabase Key: {SUPABASE_KEY[:20]}... (truncated)")
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
REVISION_INTERVALS = [1, 4, 7, 30, 180]

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
# NOTE: premium blueprint is registered LATER, after decode_token is defined (see below).
from premium_routes import premium_bp, init_premium
from analytics_routes import analytics_bp, init_analytics
app.secret_key = os.getenv("FLASK_SECRET_KEY", "change-this-to-a-strong-secret-in-production")

# Initialize rate limiter with app
limiter.init_app(app)

# ProxyFix so request.is_secure is correct behind Render's load balancer
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_port=1)

# ─── SECURITY HEADERS ───
@app.after_request
def add_security_headers(response):
    """Add security headers to all responses."""
    # Content Security Policy (relaxed for development, tighten in production)
    csp = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data: https:; "
        "font-src 'self' data:; "
        "connect-src 'self' https://*.googleapis.com https://*.supabase.co; "
        "frame-ancestors 'none';"
    )
    response.headers['Content-Security-Policy'] = csp
    
    # Prevent clickjacking
    response.headers['X-Frame-Options'] = 'DENY'
    
    # Prevent MIME type sniffing
    response.headers['X-Content-Type-Options'] = 'nosniff'
    
    # Enable XSS protection
    response.headers['X-XSS-Protection'] = '1; mode=block'
    
    # Referrer policy
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    
    # HSTS (only if HTTPS is available)
    if request.is_secure:
        response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    
    return response

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
    """Comprehensive health check endpoint."""
    health_status = {
        "status": "ok",
        "timestamp": datetime.utcnow().isoformat(),
        "services": {}
    }
    
    # Check Supabase connectivity
    if supabase:
        try:
            def check_db():
                # Simple query to test connectivity
                supabase.table('users').select('id').limit(1).execute()
            retry_database_operation(check_db, max_retries=1, backoff_factor=1)
            health_status["services"]["supabase"] = {"status": "connected", "url": SUPABASE_URL[:20] + "..."}
        except Exception as e:
            health_status["services"]["supabase"] = {"status": "disconnected", "error": str(e)}
            health_status["status"] = "degraded"
    else:
        health_status["services"]["supabase"] = {"status": "not_configured"}
        health_status["status"] = "degraded"
    
    # Check Google OAuth
    if GOOGLE_OAUTH_CLIENT_ID and GOOGLE_OAUTH_CLIENT_SECRET:
        health_status["services"]["google_oauth"] = {"status": "configured"}
    else:
        health_status["services"]["google_oauth"] = {"status": "not_configured"}
    
    # Check Gemini API
    if GEMINI_API_KEY:
        health_status["services"]["gemini_ai"] = {"status": "configured"}
    else:
        health_status["services"]["gemini_ai"] = {"status": "not_configured"}
    
    # Check Twilio
    if is_twilio_configured():
        health_status["services"]["twilio_sms"] = {"status": "configured"}
    else:
        health_status["services"]["twilio_sms"] = {"status": "not_configured"}
    
    # Environment info
    health_status["environment"] = {
        "frontend_url": FRONTEND_URL,
        "backend_url": BACKEND_URL,
        "auth_method": "JWT",
        "debug_auth": DEBUG_AUTH
    }
    
    return jsonify(health_status)

# ═══════════════════════════════════════════════════════
#  PRIVACY POLICY + TERMS  (Public, no-login pages — required for Google OAuth verification.
#  These are served by Flask so even a backend-only domain has them. The React frontend
#  ALSO has /privacy + /terms, which is what you should submit to Google for verification
#  once you own your domain.)
# ═══════════════════════════════════════════════════════
PRIVACY_HTML = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><title>LearnFlow · Privacy Policy</title>
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>body{font-family:system-ui,-apple-system,sans-serif;max-width:760px;margin:40px auto;padding:0 20px;color:#1a1a2e;line-height:1.65}
h1{font-size:2rem}h2{margin-top:2rem}code{background:#f0f0ff;padding:2px 6px;border-radius:4px}
a{color:#4f46e5}</style></head><body>
<h1>LearnFlow — Privacy Policy</h1>
<p><strong>Last updated:</strong> June 2026</p>
<p>LearnFlow ("we", "us") is a spaced-repetition study app for students. This policy explains what data we collect, why, and how you can control it.</p>
<h2>1. What we collect</h2>
<ul>
<li><strong>Account info</strong>: username, email, password hash. Created when you register.</li>
<li><strong>Learning content</strong>: titles, descriptions, PDFs/text you upload — stored encrypted in Supabase Storage.</li>
<li><strong>Optional Google Drive</strong>: with your explicit consent we sync your uploads to a folder called "Learning Intake" in <em>your own</em> Drive. We request the <code>drive.file</code> scope, which limits us to files we create — we cannot read your existing Drive.</li>
<li><strong>Optional phone number</strong>: only if you enable SMS reminders. Used to send 8 AM + 9 PM nudges via Twilio.</li>
</ul>
<h2>2. Why we ask for Google access</h2>
<p>We request the following Google OAuth scopes:</p>
<ul>
<li><code>openid</code>, <code>userinfo.email</code>, <code>userinfo.profile</code> — to let you sign in with Google.</li>
<li><code>drive.file</code> — so we can upload <em>your</em> learning files into a folder in <em>your</em> Drive. We never access files we didn\'t create.</li>
<li><code>spreadsheets</code> — to write a log of your learnings into a single LearnFlow spreadsheet in your Drive.</li>
</ul>
<p>We do <strong>not</strong> share Google data with any third party except as needed to provide the feature (i.e., Google APIs themselves).</p>
<h2>3. How we use your data</h2>
<ul>
<li>To schedule your revisions on the 1·3·6·29·179 day intervals.</li>
<li>To send you SMS reminders (only if you enable it).</li>
<li>To call Google Gemini for AI summaries / flashcards / quizzes when you press those buttons (Premium feature).</li>
</ul>
<h2>4. Data deletion</h2>
<p>Email <a href="mailto:learnflow.app@gmail.com">learnflow.app@gmail.com</a> and we delete your account, files, and Drive credentials within 7 days. You can also disconnect Drive any time from <em>Profile → Google Drive → Disconnect</em>.</p>
<h2>5. Security</h2>
<p>Passwords are bcrypt-hashed. Auth uses JWT (HS256) with a 30-day expiry. Drive credentials are stored encrypted in our database (Supabase row-level security).</p>
<h2>6. Contact</h2>
<p>Questions: <a href="mailto:learnflow.app@gmail.com">learnflow.app@gmail.com</a></p>
<p><a href="/">← Back to LearnFlow</a> · <a href="/terms">Terms of Service</a></p>
</body></html>"""

TERMS_HTML = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><title>LearnFlow · Terms of Service</title>
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>body{font-family:system-ui,-apple-system,sans-serif;max-width:760px;margin:40px auto;padding:0 20px;color:#1a1a2e;line-height:1.65}
h1{font-size:2rem}h2{margin-top:2rem}a{color:#4f46e5}</style></head><body>
<h1>LearnFlow — Terms of Service</h1>
<p><strong>Last updated:</strong> June 2026</p>
<p>By using LearnFlow you agree to these terms.</p>
<h2>1. The service</h2>
<p>LearnFlow helps students remember what they study using spaced repetition. We offer a Free plan, a Core plan, and a Premium plan (currently free for 30 days via the launch coupons LAUNCH30 / STUDENT30 / FIRST100 / LEARNFREE).</p>
<h2>2. Your responsibilities</h2>
<ul><li>Don\'t upload illegal, copyrighted (without permission), or harmful content.</li>
<li>Don\'t share your account.</li>
<li>Don\'t abuse the AI features (rate limits apply).</li></ul>
<h2>3. Payments</h2>
<p>The current checkout is a demo / launch promotion — no real payment is taken when a launch coupon is applied. Premium activates for 30 days from coupon redemption.</p>
<h2>4. Cancellation</h2>
<p>You can stop using LearnFlow any time. Email us to delete your data.</p>
<h2>5. Liability</h2>
<p>LearnFlow is provided "as is" without warranty. We are not liable for grades, exam outcomes, or memory failures.</p>
<p><a href="/">← Back to LearnFlow</a> · <a href="/privacy">Privacy Policy</a></p>
</body></html>"""

@app.route("/privacy")
def privacy():
    # Serves a real HTML privacy policy (no JSON, no login required) — required
    # for Google OAuth homepage / consent-screen verification.
    from flask import Response
    return Response(PRIVACY_HTML, mimetype="text/html")

@app.route("/terms")
def terms():
    from flask import Response
    return Response(TERMS_HTML, mimetype="text/html")


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
#  REGISTER PREMIUM BLUEPRINT
#  (must be done AFTER decode_token is defined, otherwise NameError)
# ════════════════════════════════════════════════════════════════
init_premium(app, supabase, logger, decode_token)
app.register_blueprint(premium_bp)
init_analytics(supabase, decode_token)
app.register_blueprint(analytics_bp)


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


# ─── INPUT VALIDATION ───
import re
from urllib.parse import urlparse

def validate_email(email):
    """Validate email format."""
    if not email:
        return False, "Email is required"
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(pattern, email):
        return False, "Invalid email format"
    if len(email) > 255:
        return False, "Email too long"
    return True, None

def validate_username(username):
    """Validate username format."""
    if not username:
        return False, "Username is required"
    if len(username) < 3:
        return False, "Username must be at least 3 characters"
    if len(username) > 30:
        return False, "Username too long (max 30 characters)"
    pattern = r'^[a-zA-Z0-9_-]+$'
    if not re.match(pattern, username):
        return False, "Username can only contain letters, numbers, underscores, and hyphens"
    return True, None

def validate_password(password):
    """Validate password strength."""
    if not password:
        return False, "Password is required"
    if len(password) < 6:
        return False, "Password must be at least 6 characters"
    if len(password) > 128:
        return False, "Password too long"
    return True, None

def validate_url(url):
    """Validate URL format and safety."""
    if not url:
        return True, None  # Optional field
    try:
        parsed = urlparse(url)
        if not parsed.scheme or not parsed.netloc:
            return False, "Invalid URL format"
        if parsed.scheme not in ['http', 'https']:
            return False, "URL must use http or https"
        # Block localhost and private IPs in production
        if parsed.hostname in ['localhost', '127.0.0.1', '0.0.0.0']:
            return False, "URL cannot point to localhost"
        return True, None
    except Exception:
        return False, "Invalid URL format"

def validate_phone_number(phone):
    """Validate phone number format (international)."""
    if not phone:
        return True, None  # Optional field
    # Remove spaces, dashes, parentheses
    cleaned = re.sub(r'[\s\-\(\)]', '', phone)
    # Basic international format: + followed by 10-15 digits
    pattern = r'^\+[1-9]\d{9,14}$'
    if not re.match(pattern, cleaned):
        return False, "Invalid phone number format. Use international format: +1234567890"
    return True, None

def validate_learning_id(learning_id):
    """Validate learning ID is a positive integer."""
    try:
        lid = int(learning_id)
        if lid <= 0:
            return False, "Learning ID must be a positive integer"
        return True, None
    except (ValueError, TypeError):
        return False, "Invalid learning ID format"

def validate_pagination_params(page, limit):
    """Validate pagination parameters."""
    try:
        page = int(page) if page else 1
        limit = int(limit) if limit else 20
        if page < 1:
            return False, "Page must be at least 1"
        if limit < 1 or limit > 100:
            return False, "Limit must be between 1 and 100"
        return True, None
    except (ValueError, TypeError):
        return False, "Invalid pagination parameters"

# ─── DATABASE HELPERS ───
import time

def retry_database_operation(operation, max_retries=3, backoff_factor=2):
    """
    Retry database operations with exponential backoff.
    Handles transient network errors and connection issues.
    """
    last_error = None
    for attempt in range(max_retries):
        try:
            return operation()
        except Exception as e:
            last_error = e
            error_msg = str(e).lower()
            # Check if it's a transient error (network-related)
            is_transient = any(keyword in error_msg for keyword in [
                'name or service not known',
                'connection',
                'timeout',
                'network',
                'temporary'
            ])
            
            if not is_transient:
                # Non-transient error, don't retry
                raise
            
            if attempt < max_retries - 1:
                wait_time = backoff_factor ** attempt
                logger.warning(f"Database operation failed (attempt {attempt + 1}/{max_retries}), retrying in {wait_time}s: {e}")
                time.sleep(wait_time)
    
    logger.error(f"Database operation failed after {max_retries} retries: {last_error}")
    raise last_error

def get_user_by_username(username):
    if not supabase:
        return None
    try:
        def operation():
            r = supabase.table('users').select('*').eq('username', username).execute()
            return r.data[0] if r.data else None
        return retry_database_operation(operation)
    except Exception as e:
        logger.error(f"get_user_by_username error: {e}")
        return None

def get_user_by_email(email):
    if not supabase:
        return None
    try:
        def operation():
            r = supabase.table('users').select('*').eq('email', email).execute()
            return r.data[0] if r.data else None
        return retry_database_operation(operation)
    except Exception as e:
        logger.error(f"get_user_by_email error: {e}")
        return None


def get_user_by_id(user_id):
    if not supabase:
        return None
    try:
        def operation():
            r = supabase.table('users').select('*').eq('id', user_id).execute()
            return r.data[0] if r.data else None
        return retry_database_operation(operation)
    except Exception as e:
        logger.error(f"get_user_by_id error: {e}")
        return None

def create_user(username, password_hash, email):
    """Returns (user_id, error_message). user_id is None on failure."""
    if not supabase:
        return None, "Database not configured (SUPABASE_URL/SUPABASE_KEY missing)"
    try:
        def operation():
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
        return retry_database_operation(operation)
    except Exception as e:
        err = f"{type(e).__name__}: {str(e)}"
        logger.error(f"Create user error: {err}\n{traceback.format_exc()}")
        return None, err

def get_user_state(user_id):
    if not supabase: return None
    try:
        r = supabase.table('user_state').select('*').eq('user_id', user_id).execute()
        return r.data[0] if r.data else None
    except Exception as e:
        logger.error(f"get_user_state error: {e}")
        return None

def update_user_state(user_id, **kwargs):
    if not supabase: return False
    try:
        supabase.table('user_state').update(kwargs).eq('user_id', user_id).execute()
        return True
    except Exception as e:
        logger.error(f"update_user_state error: {e}")
        return False

def save_drive_credentials(user_id, creds_json):
    if not supabase: return False
    try:
        supabase.table('user_state').update({
            'google_drive_credentials': creds_json,
            'drive_connected': True
        }).eq('user_id', user_id).execute()
        return True
    except Exception as e:
        logger.error(f"save_drive_credentials error: {e}")
        return False

def get_drive_credentials(user_id):
    if not supabase: return None
    try:
        r = supabase.table('user_state').select('google_drive_credentials').eq('user_id', user_id).execute()
        if r.data and r.data[0]['google_drive_credentials']:
            return r.data[0]['google_drive_credentials']
        return None
    except Exception as e:
        logger.error(f"get_drive_credentials error: {e}")
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
    except Exception as e:
        logger.error(f"update_streak error: {e}")
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
        "description": "Every new learning item is scheduled for review on Day 1, 4, 7, 30 and 180. Missed reviews remain overdue until completed, so weaker memories keep resurfacing."
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
        self.model = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
        self.api_url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent"
        self.api_key = os.getenv("GEMINI_API_KEY")
        self.headers = {"Content-Type": "application/json"}

    def _call_gemini(self, prompt, timeout=30):
        """Helper method to call Gemini API with error handling and retry."""
        if not self.api_key:
            logger.error("GEMINI_API_KEY not configured")
            return None
        
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0.7,
                "maxOutputTokens": 2048
            }
        }
        
        for attempt in range(3):  # Retry up to 3 times
            try:
                r = requests.post(
                    self.api_url, 
                    headers=self.headers, 
                    params={"key": self.api_key}, 
                    json=payload, 
                    timeout=timeout
                )
                r.raise_for_status()
                return r.json()["candidates"][0]["content"]["parts"][0]["text"]
            except requests.exceptions.Timeout:
                logger.warning(f"Gemini API timeout (attempt {attempt + 1}/3)")
                if attempt < 2:
                    continue
                return None
            except requests.exceptions.HTTPError as e:
                logger.error(f"Gemini API HTTP error: {e}")
                return None
            except Exception as e:
                logger.error(f"Gemini API error: {e}")
                return None
        
        return None

    def generate(self, snippet):
        """Generate heading and description for learning material."""
        if not snippet or not snippet.strip():
            return "Untitled Item", "No content provided."
        if not self.api_key:
            return "Generated Title", "AI generation not configured."
        
        prompt = (
            "Generate concise learning metadata.\n\n"
            "Rules:\n- Heading: max 8 words\n- Description: 1-2 short sentences\n"
            "- No markdown or labels\n\n"
            f"Content:\n{snippet[:1500]}"
        )
        
        text = self._call_gemini(prompt)
        if not text:
            return "Generated Heading", "Auto-description failed."
        
        lines = [l.strip() for l in text.splitlines() if l.strip()]
        heading = lines[0] if lines else "Untitled"
        desc = " ".join(lines[1:]) if len(lines) > 1 else "Brief summary."
        return heading, desc

    def generate_summary(self, content):
        """Generate a comprehensive summary of the content."""
        if not self.api_key:
            return None
        
        prompt = (
            "Generate a comprehensive summary of the following content.\n\n"
            "Rules:\n"
            "- 3-5 bullet points\n"
            "- Each bullet point should be 1-2 sentences\n"
            "- Focus on key concepts and main ideas\n"
            "- Use plain text, no markdown\n\n"
            f"Content:\n{content[:3000]}"
        )
        
        return self._call_gemini(prompt, timeout=45)

    def generate_keywords(self, content):
        """Generate key terms and concepts from the content."""
        if not self.api_key:
            return None
        
        prompt = (
            "Extract 5-10 key terms and concepts from the following content.\n\n"
            "Rules:\n"
            "- Return as a comma-separated list\n"
            "- Focus on important terminology\n"
            "- No explanations, just the terms\n\n"
            f"Content:\n{content[:3000]}"
        )
        
        return self._call_gemini(prompt, timeout=30)

    def generate_quiz(self, content):
        """Generate a quiz based on the content."""
        if not self.api_key:
            return None
        
        prompt = (
            "Generate a quiz with 5 multiple-choice questions based on the following content.\n\n"
            "Rules:\n"
            "- Format: Question | Option A | Option B | Option C | Option D | Correct Answer\n"
            "- Each question on a new line\n"
            "- Test understanding of key concepts\n"
            "- Correct answer should be A, B, C, or D\n\n"
            f"Content:\n{content[:3000]}"
        )
        
        return self._call_gemini(prompt, timeout=45)

    def generate_flashcards(self, content):
        """Generate flashcards from the content."""
        if not self.api_key:
            return None
        
        prompt = (
            "Generate 8-10 flashcards from the following content.\n\n"
            "Rules:\n"
            "- Format: Front | Back\n"
            "- Each flashcard on a new line\n"
            "- Front: question or term\n"
            "- Back: answer or definition\n"
            "- Focus on key facts and concepts\n\n"
            f"Content:\n{content[:3000]}"
        )
        
        return self._call_gemini(prompt, timeout=45)

    def generate_mindmap(self, content):
        """Generate a mindmap structure from the content."""
        if not self.api_key:
            return None
        
        prompt = (
            "Generate a mindmap structure from the following content.\n\n"
            "Rules:\n"
            "- Format: Main Topic -> Subtopic 1, Subtopic 2 -> Detail 1, Detail 2\n"
            "- Use arrows (->) to show hierarchy\n"
            "- Use commas to separate items at the same level\n"
            "- 3-4 levels deep maximum\n"
            "- Focus on main topics and key relationships\n\n"
            f"Content:\n{content[:3000]}"
        )
        
        return self._call_gemini(prompt, timeout=45)

    def generate_revision_notes(self, content):
        """Generate structured revision notes from the content."""
        if not self.api_key:
            return None
        
        prompt = (
            "Generate structured revision notes from the following content.\n\n"
            "Rules:\n"
            "- Format: ## Topic\n- Key point 1\n- Key point 2\n\n"
            "- Use markdown headings for main topics\n"
            "- Use bullet points for key information\n"
            "- Include examples where relevant\n"
            "- Focus on exam-relevant information\n\n"
            f"Content:\n{content[:3000]}"
        )
        
        return self._call_gemini(prompt, timeout=60)

    def generate_all_outputs(self, content):
        """Generate all AI outputs at once."""
        if not self.api_key:
            return None
        
        outputs = {
            "summary": self.generate_summary(content),
            "keywords": self.generate_keywords(content),
            "quiz": self.generate_quiz(content),
            "flashcards": self.generate_flashcards(content),
            "mindmap": self.generate_mindmap(content),
            "revision_notes": self.generate_revision_notes(content)
        }
        
        # Filter out None values
        return {k: v for k, v in outputs.items() if v is not None}

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
    """Build Google Credentials from stored token data with refresh token support."""
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
    except Exception as e:
        logger.error(f"_build_creds error for user {user_id}: {e}")
        return None

def verify_drive_permissions(service):
    """Verify that Drive API has proper permissions by attempting a simple operation."""
    if not service:
        return False, "Service not initialized"
    try:
        # Try to list files - this verifies Drive API access
        service.files().list(pageSize=1, fields="files(id)").execute()
        return True, "Permissions verified"
    except Exception as e:
        logger.error(f"Drive permissions verification failed: {e}")
        return False, str(e)

def verify_drive_connection(user_id):
    """
    Verify Drive connection is actually working by testing credentials and API access.
    Returns (is_connected, status_message)
    """
    state = get_user_state(user_id)
    if not state or not state.get('drive_connected'):
        return False, "not_connected"
    
    cj = get_drive_credentials(user_id)
    if not cj:
        return False, "credentials_missing"
    
    try:
        service = get_drive_service(user_id)
        if not service:
            return False, "service_failed"
        
        verified, msg = verify_drive_permissions(service)
        if not verified:
            return False, f"permissions_failed: {msg}"
        
        return True, "connected"
    except Exception as e:
        logger.error(f"Drive connection verification failed for user {user_id}: {e}")
        return False, f"error: {str(e)}"

def get_drive_service(user_id):
    """Get Drive service with credential refresh support."""
    creds = _build_creds(user_id)
    if not creds:
        return None
    try:
        # Refresh token if expired
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
            # Save refreshed credentials
            cd = {
                'token': creds.token,
                'refresh_token': creds.refresh_token,
                'token_uri': creds.token_uri,
                'client_id': creds.client_id,
                'client_secret': creds.client_secret,
                'scopes': list(creds.scopes) if creds.scopes else SCOPES
            }
            save_drive_credentials(user_id, json.dumps(cd))
            logger.info(f"Refreshed Drive credentials for user {user_id}")
        return build("drive", "v3", credentials=creds)
    except Exception as e:
        logger.error(f"get_drive_service error for user {user_id}: {e}")
        return None

def get_sheets_service(user_id):
    """Get Sheets service with credential refresh support."""
    creds = _build_creds(user_id)
    if not creds:
        return None
    try:
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
            cd = {
                'token': creds.token,
                'refresh_token': creds.refresh_token,
                'token_uri': creds.token_uri,
                'client_id': creds.client_id,
                'client_secret': creds.client_secret,
                'scopes': list(creds.scopes) if creds.scopes else SCOPES
            }
            save_drive_credentials(user_id, json.dumps(cd))
        return build("sheets", "v4", credentials=creds)
    except Exception as e:
        logger.error(f"get_sheets_service error for user {user_id}: {e}")
        return None

def get_or_create_folder(service):
    """Get or create the Learning Intake folder in Drive."""
    if not service:
        return None
    try:
        r = service.files().list(
            q=f"name='{APP_FOLDER_NAME}' and mimeType='application/vnd.google-apps.folder' and trashed=false",
            fields="files(id)"
        ).execute()
        files = r.get("files", [])
        if files:
            logger.info(f"Found existing Drive folder: {files[0]['id']}")
            return files[0]["id"]
        f = service.files().create(
            body={"name": APP_FOLDER_NAME, "mimeType": "application/vnd.google-apps.folder"},
            fields="id"
        ).execute()
        logger.info(f"Created new Drive folder: {f['id']}")
        return f["id"]
    except Exception as e:
        logger.error(f"get_or_create_folder error: {e}")
        return None

def upload_to_drive(user_id, supabase_path, filename):
    """
    Upload file to Google Drive.
    Returns dict with file_id and drive_link, or None on failure.
    """
    try:
        service = get_drive_service(user_id)
        if not service:
            logger.error(f"Cannot get Drive service for user {user_id}")
            return None
        
        # Verify permissions before upload
        verified, msg = verify_drive_permissions(service)
        if not verified:
            logger.error(f"Drive permissions check failed: {msg}")
            return None
        
        folder_id = get_or_create_folder(service)
        if not folder_id:
            logger.error("Cannot get or create Drive folder")
            return None
        
        data = download_from_supabase(supabase_path)
        if not data:
            logger.error("Cannot download from Supabase")
            return None
        
        with NamedTemporaryFile(delete=False) as tmp:
            tmp.write(data)
            tp = tmp.name
        
        media = MediaFileUpload(tp, resumable=True)
        uploaded = service.files().create(
            body={"name": filename, "parents": [folder_id]},
            media_body=media, 
            fields="id"
        ).execute()
        
        # Make file publicly readable
        service.permissions().create(
            fileId=uploaded["id"],
            body={"type": "anyone", "role": "reader"}
        ).execute()
        
        os.unlink(tp)
        
        file_id = uploaded["id"]
        drive_link = f"https://drive.google.com/file/d/{file_id}/view"
        
        logger.info(f"Successfully uploaded to Drive: file_id={file_id}, link={drive_link}")
        
        return {
            "file_id": file_id,
            "drive_link": drive_link
        }
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
@limiter.limit("5 per hour")
def api_register():
    try:
        data = request.get_json(force=True, silent=True) or {}
        username = data.get("username", "").strip()
        password = data.get("password", "").strip()
        email = data.get("email", "").strip()

        # Validate inputs
        valid, error = validate_username(username)
        if not valid:
            return jsonify({"error": error}), 400
        
        valid, error = validate_email(email)
        if not valid:
            return jsonify({"error": error}), 400
        
        valid, error = validate_password(password)
        if not valid:
            return jsonify({"error": error}), 400

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
@limiter.limit("10 per hour")
def api_login():
    try:
        data = request.get_json(force=True, silent=True) or {}
        username = data.get("username", "").strip()
        password = data.get("password", "").strip()
        
        # Validate inputs
        valid, error = validate_username(username)
        if not valid:
            return jsonify({"error": error}), 400
        
        valid, error = validate_password(password)
        if not valid:
            return jsonify({"error": error}), 400
        
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


def _fetch_premium_state(user_id):
    """Read premium_expires_at from user_state and return {is_premium, days_left, expires_at}.
    Safe to call even if the column doesn't exist yet — returns is_premium=False."""
    if not supabase:
        return {"is_premium": False, "days_left": 0, "expires_at": None}
    try:
        r = supabase.table('user_state').select('premium_expires_at').eq('user_id', user_id).execute()
        if not r.data:
            return {"is_premium": False, "days_left": 0, "expires_at": None}
        exp = r.data[0].get('premium_expires_at')
        if not exp:
            return {"is_premium": False, "days_left": 0, "expires_at": None}
        from datetime import timezone as _tz
        exp_dt = datetime.fromisoformat(exp.replace('Z', '+00:00'))
        now = datetime.now(_tz.utc)
        if exp_dt <= now:
            return {"is_premium": False, "days_left": 0, "expires_at": exp}
        days_left = max(0, (exp_dt - now).days + 1)
        return {"is_premium": True, "days_left": days_left, "expires_at": exp}
    except Exception as e:
        logger.warning(f"_fetch_premium_state failed: {e}")
        return {"is_premium": False, "days_left": 0, "expires_at": None}


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
        
        # Verify Drive connection with actual API test
        dc, drive_status_msg = verify_drive_connection(user_id)
        
        # FIX: include premium info on /me so the React useAuth hook reflects
        # premium status immediately after redemption (no more "claim again" loop)
        premium_info = _fetch_premium_state(user_id)
        logger.info(f"[ME OK] user_id={user_id} premium={premium_info['is_premium']} drive_connected={dc} drive_status={drive_status_msg}")
        return jsonify({
            "user": {
                "id": user_id,
                "username": username,
                "drive_connected": dc,
                "drive_status": drive_status_msg,
                "notification_phone": state.get('notification_phone'),
                "sms_notifications_enabled": bool(state.get('sms_notifications_enabled')),
                "notification_timezone": state.get('notification_timezone') or "UTC",
                "notification_hour": state.get('notification_hour', DEFAULT_NOTIFICATION_HOUR),
                "twilio_configured": is_twilio_configured(),
                "is_premium": premium_info["is_premium"],
                "premium": premium_info,
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

    # Validate phone number
    normalized_phone = None
    if raw_phone:
        valid, error = validate_phone_number(raw_phone)
        if not valid:
            return jsonify({"error": error}), 400
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
@limiter.limit("10 per hour")
def api_send_daily_notifications():
    """Cron job endpoint for sending daily SMS reminders."""
    provided_secret = request.headers.get("X-Notification-Secret", "")
    if not DAILY_NOTIFICATION_SECRET or provided_secret != DAILY_NOTIFICATION_SECRET:
        logger.warning("Unauthorized cron job attempt")
        return jsonify({"error": "Unauthorized"}), 403
    if not supabase:
        logger.error("Database not configured for cron job")
        return jsonify({"error": "Database not configured"}), 503
    if not is_twilio_configured():
        logger.warning("Twilio not configured for cron job")
        return jsonify({"error": "Twilio is not configured"}), 503

    logger.info("Starting daily notification cron job")
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

        # Allow a 1-hour window for delivery to account for cron timing
        if abs(local_now.hour - target_hour) > 1:
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
        
        # Retry SMS sending up to 2 times
        sms_sent = False
        for attempt in range(2):
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
                sms_sent = True
                logger.info(f"Daily SMS sent to user {user_id} (attempt {attempt + 1})")
                break
            except Exception as exc:
                logger.error(f"Daily SMS failed for {user_id} (attempt {attempt + 1}): {exc}")
                if attempt == 1:  # Last attempt failed
                    skipped.append({"user_id": user_id, "reason": f"send_failed: {exc}"})

    logger.info(f"Cron job completed: sent={len(processed)}, skipped={len(skipped)}")
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
        # OAuth scopes for Google Sign-In
        oauth_scopes = [
            "openid",
            "https://www.googleapis.com/auth/userinfo.email",
            "https://www.googleapis.com/auth/userinfo.profile"
        ]
        flow = Flow.from_client_config({
            "web": {
                "client_id": GOOGLE_OAUTH_CLIENT_ID,
                "client_secret": GOOGLE_OAUTH_CLIENT_SECRET,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [GOOGLE_LOGIN_REDIRECT]
            }
        }, scopes=oauth_scopes, **flow_kwargs)
        flow.redirect_uri = GOOGLE_LOGIN_REDIRECT
        flow.fetch_token(authorization_response=request.url)
        creds = flow.credentials
        
        # Log token details for debugging (without exposing secrets)
        logger.info(f"[Google OAuth] Token received, has refresh token: {bool(creds.refresh_token)}")
        logger.info(f"[Google OAuth] Token scopes: {creds.scopes}")
        
        # Verify we got the required scopes
        required_scopes = {"openid", "https://www.googleapis.com/auth/userinfo.email"}
        if not required_scopes.issubset(set(creds.scopes)):
            logger.error(f"[Google OAuth] Missing required scopes. Got: {creds.scopes}")
            return flask_redirect(f"{FRONTEND_URL}/login?error=google_scopes_missing")
        
        info = requests.get('https://www.googleapis.com/oauth2/v3/userinfo',
                            headers={'Authorization': f'Bearer {creds.token}'}).json()
        email = info.get('email')
        if not email:
            logger.error("[Google OAuth] No email in user info response")
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
                    logger.error(f"[Google register] Failed to create user for email={email}: {err}")
                    return flask_redirect(f"{FRONTEND_URL}/register?error=signup_failed")
                user = get_user_by_email(email)
                logger.info(f"[Google register OK] user_id={uid} email={email}")

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
        
        # Verify we got refresh token (required for long-term access)
        if not creds.refresh_token:
            logger.warning(f"[Drive callback] No refresh token received for user {uid}. Access may expire.")
        
        # Verify Drive API scope is present
        drive_scope = "https://www.googleapis.com/auth/drive.file"
        if drive_scope not in creds.scopes:
            logger.error(f"[Drive callback] Missing Drive scope. Got: {creds.scopes}")
            return flask_redirect(f"{FRONTEND_URL}/dashboard?drive=error&reason=missing_scope")
        
        cd = {
            'token': creds.token,
            'refresh_token': creds.refresh_token,
            'token_uri': creds.token_uri,
            'client_id': creds.client_id,
            'client_secret': creds.client_secret,
            'scopes': list(creds.scopes) if creds.scopes else SCOPES
        }
        saved = save_drive_credentials(uid, json.dumps(cd))
        if not saved:
            logger.error(f"[Drive callback] Failed to save credentials for user {uid}")
            return flask_redirect(f"{FRONTEND_URL}/dashboard?drive=error&reason=save_failed")
        
        # Verify the connection works immediately
        service = get_drive_service(uid)
        if not service:
            logger.error(f"[Drive callback] Failed to create Drive service for user {uid}")
            return flask_redirect(f"{FRONTEND_URL}/dashboard?drive=error&reason=service_failed")
        
        verified, msg = verify_drive_permissions(service)
        if not verified:
            logger.error(f"[Drive callback] Drive permissions verification failed: {msg}")
            return flask_redirect(f"{FRONTEND_URL}/dashboard?drive=error&reason=permissions_failed")
        
        logger.info(f"[Drive callback] Drive connected and verified for user_id={uid}")
        return flask_redirect(f"{FRONTEND_URL}/dashboard?drive=connected")
    except Exception as e:
        logger.error(f"Drive callback error: {e}\n{traceback.format_exc()}")
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
@limiter.limit("20 per hour")
def api_preview():
    uid = request.user_id
    file = request.files.get("file")
    url_input = request.form.get("url", "").strip()
    text_input = request.form.get("text", "").strip()

    if file and file.filename:
        # Validate file size (max 10MB)
        file.seek(0, os.SEEK_END)
        file_size = file.tell()
        file.seek(0)
        if file_size > 10 * 1024 * 1024:  # 10MB
            return jsonify({"error": "File too large (max 10MB)"}), 400
        
        # Validate file type
        allowed_extensions = {'.pdf', '.docx', '.doc', '.txt', '.md'}
        ext = Path(file.filename).suffix.lower()
        if ext not in allowed_extensions:
            return jsonify({"error": f"File type not allowed. Allowed: {', '.join(allowed_extensions)}"}), 400
        
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
        # Validate URL
        valid, error = validate_url(url_input)
        if not valid:
            return jsonify({"error": error}), 400
        content = extract_from_url(url_input)
        heading, desc = gemini.generate(content)
        return jsonify({
            "heading": heading, "description": desc,
            "source": "url", "url": url_input,
            "content_snippet": content[:500]
        })
    elif text_input:
        if len(text_input) > 50000:  # Max 50KB of text
            return jsonify({"error": "Text too long (max 50,000 characters)"}), 400
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
    drive_file_id = None
    state = get_user_state(uid)
    dc = state and state.get('drive_connected') and get_drive_credentials(uid)
    if dc and source == "file" and supabase_path and filename:
        drive_result = upload_to_drive(uid, supabase_path, filename)
        if drive_result:
            drive_link = drive_result.get('drive_link')
            drive_file_id = drive_result.get('file_id')
            logger.info(f"Drive upload successful: file_id={drive_file_id}, link={drive_link}")

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
        if drive_file_id:
            insert_data['drive_file_id'] = drive_file_id

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


# ─── AI ARTIFACTS ENDPOINTS ───
@app.route("/api/ai/generate", methods=["POST"])
@login_required
@limiter.limit("10 per hour")
def api_ai_generate():
    """Generate AI artifacts for a learning item."""
    uid = request.user_id
    data = request.get_json(force=True, silent=True) or {}
    learning_id = data.get("learning_id")
    artifact_types = data.get("types", ["summary", "keywords", "quiz", "flashcards", "mindmap", "revision_notes"])
    
    # Validate learning_id
    valid, error = validate_learning_id(learning_id)
    if not valid:
        return jsonify({"error": error}), 400
    
    # Check premium status
    premium_info = _fetch_premium_state(uid)
    if not premium_info["is_premium"]:
        logger.warning(f"[AI GENERATE] Non-premium user {uid} attempted to generate artifacts")
        return jsonify({"error": "Premium required for AI features"}), 402
    
    try:
        # Get learning content
        r = supabase.table('learnings').select('*').eq('id', learning_id).eq('user_id', uid).execute()
        if not r.data:
            logger.warning(f"[AI GENERATE] Learning {learning_id} not found for user {uid}")
            return jsonify({"error": "Learning not found"}), 404
        
        learning = r.data[0]
        content = (learning.get('content') or learning.get('title') or "")[:6000]
        if not content.strip():
            return jsonify({"error": "No content to process"}), 400
        
        # Validate artifact types
        valid_types = {"summary", "keywords", "quiz", "flashcards", "mindmap", "revision_notes"}
        invalid_types = [t for t in artifact_types if t not in valid_types]
        if invalid_types:
            return jsonify({"error": f"Invalid artifact types: {invalid_types}"}), 400
        
        # Generate requested artifacts
        results = {}
        for artifact_type in artifact_types:
            if artifact_type == "summary":
                results["summary"] = gemini.generate_summary(content)
            elif artifact_type == "keywords":
                results["keywords"] = gemini.generate_keywords(content)
            elif artifact_type == "quiz":
                results["quiz"] = gemini.generate_quiz(content)
            elif artifact_type == "flashcards":
                results["flashcards"] = gemini.generate_flashcards(content)
            elif artifact_type == "mindmap":
                results["mindmap"] = gemini.generate_mindmap(content)
            elif artifact_type == "revision_notes":
                results["revision_notes"] = gemini.generate_revision_notes(content)
        
        # Store artifacts in database
        saved_count = 0
        for artifact_type, artifact_content in results.items():
            if artifact_content:
                try:
                    supabase.table('ai_artifacts').insert({
                        'learning_id': learning_id,
                        'artifact_type': artifact_type,
                        'content': artifact_content
                    }).execute()
                    saved_count += 1
                    logger.info(f"Saved AI artifact: {artifact_type} for learning_id={learning_id}")
                except Exception as e:
                    logger.error(f"Failed to save artifact {artifact_type}: {e}")
        
        logger.info(f"[AI GENERATE OK] user_id={uid} learning_id={learning_id} saved={saved_count}/{len(results)}")
        return jsonify({
            "message": "AI artifacts generated",
            "learning_id": learning_id,
            "artifacts": results,
            "saved_count": saved_count
        })
    except Exception as e:
        logger.error(f"AI generation error: {e}\n{traceback.format_exc()}")
        return jsonify({"error": f"AI generation failed: {str(e)}"}), 500


@app.route("/api/ai/artifacts/<int:learning_id>", methods=["GET"])
@login_required
def api_get_ai_artifacts(learning_id):
    """Get all AI artifacts for a learning item."""
    uid = request.user_id
    
    try:
        # Verify ownership
        lr = supabase.table('learnings').select('id').eq('id', learning_id).eq('user_id', uid).execute()
        if not lr.data:
            logger.warning(f"[AI ARTIFACTS GET] Learning {learning_id} not found for user {uid}")
            return jsonify({"error": "Learning not found"}), 404
        
        # Get artifacts
        ar = supabase.table('ai_artifacts').select('*').eq('learning_id', learning_id).execute()
        
        artifacts = {}
        for artifact in ar.data:
            artifacts[artifact['artifact_type']] = artifact['content']
        
        logger.info(f"[AI ARTIFACTS GET OK] user_id={uid} learning_id={learning_id} count={len(artifacts)}")
        return jsonify({
            "learning_id": learning_id,
            "artifacts": artifacts
        })
    except Exception as e:
        logger.error(f"Get artifacts error: {e}\n{traceback.format_exc()}")
        return jsonify({"error": f"Failed to get artifacts: {str(e)}"}), 500


# ─── REVISIONS ───
@app.route("/api/revisions/today")
@login_required
def api_today():
    # FIX: frontend reads `r.data?.revisions` everywhere. The old endpoint returned
    # a bare array, which silently became `undefined` on the client → empty dashboard.
    uid = request.user_id
    today = date.today().isoformat()
    cleanup_old_files(uid)
    r = supabase.table('revisions').select('*').eq('user_id', uid).eq('scheduled_date', today).eq('completed', False).order('stage').execute()
    return jsonify({"revisions": [_build_revision(row) for row in r.data]})

@app.route("/api/revisions/overdue")
@login_required
def api_overdue():
    uid = request.user_id
    today = date.today().isoformat()
    r = supabase.table('revisions').select('*').eq('user_id', uid).lt('scheduled_date', today).eq('completed', False).order('scheduled_date').execute()
    return jsonify({"revisions": [_build_revision(row) for row in r.data]})

@app.route("/api/revisions/completed")
@login_required
def api_completed():
    # FIX: History page expects { revisions: [...] }; also include all-time completed,
    # not only those completed today (the old query was useless for a History page).
    uid = request.user_id
    r = supabase.table('revisions').select('*').eq('user_id', uid).eq('completed', True).order('completed_date', desc=True).limit(200).execute()
    return jsonify({"revisions": [_build_revision(row) for row in r.data]})

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
    # FIX: also return the flat array under `revisions` so the frontend can use either shape.
    return jsonify({"revisions": revisions, "grouped": grouped, "total": len(revisions)})

@app.route("/api/revisions/stats")
@login_required
def api_stats():
    # FIX: Dashboard reads stats.current_streak and stats.total_learnings, but the
    # old endpoint only returned `streak`. Now we return BOTH naming styles plus
    # total_learnings so the dashboard cards don't show 0 / undefined.
    uid = request.user_id
    stats = get_revision_stats(uid)
    streak, _ = get_user_streak(uid)
    stats['streak'] = streak
    stats['current_streak'] = streak                       # alias for the React Dashboard
    try:
        total_learnings = len(supabase.table('learnings').select('id').eq('user_id', uid).execute().data or [])
    except Exception:
        total_learnings = 0
    stats['total_learnings'] = total_learnings
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
    # FIX: PremiumLab.jsx reads r.data?.learnings — wrap accordingly.
    uid = request.user_id
    r = supabase.table('learnings').select('*').eq('user_id', uid).order('created_at', desc=True).limit(50).execute()
    rows = r.data or []
    # Add `heading` alias so the React code that reads `l.heading || l.title` always finds something.
    for row in rows:
        if 'heading' not in row:
            row['heading'] = row.get('title')
    return jsonify({"learnings": rows})


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


# ─── ADMIN ENDPOINTS ───
@app.route("/api/admin/metrics")
@login_required
def api_admin_metrics():
    """Get system metrics for admin dashboard."""
    uid = request.user_id
    # TODO: Add admin role check
    try:
        # Get cron execution stats
        cron_executions = supabase.table('cron_executions').select('*').order('started_at', desc=True).limit(10).execute().data or []
        
        # Get recent metrics
        recent_metrics = supabase.table('metrics').select('*').order('timestamp', desc=True).limit(100).execute().data or []
        
        # Get dead letter queue count
        dlq_count = len(supabase.table('dead_letter_queue').select('id').execute().data or [])
        
        # Calculate stats
        successful_cron = len([e for e in cron_executions if e.get('status') == 'completed'])
        failed_cron = len([e for e in cron_executions if e.get('status') == 'failed'])
        
        last_execution = cron_executions[0].get('started_at') if cron_executions else None
        
        return jsonify({
            "cron": {
                "last_execution": last_execution,
                "successful": successful_cron,
                "failed": failed_cron,
                "retried": 0  # TODO: Track retries
            },
            "sms": {
                "sent": 0,  # TODO: Track SMS metrics
                "failed": 0,
                "pending": 0
            },
            "queue": {
                "length": 0,  # TODO: Track queue length
                "processing": 0
            },
            "dead_letter": {
                "count": dlq_count
            },
            "performance": {
                "avg_response_time": 0,  # TODO: Track performance
                "p95_response_time": 0,
                "requests_per_minute": 0
            },
            "errors": []  # TODO: Track recent errors
        })
    except Exception as e:
        logger.error(f"Admin metrics error: {e}")
        return jsonify({"error": "Failed to fetch metrics"}), 500


@app.route("/api/admin/dead-letter")
@login_required
def api_admin_dead_letter():
    """Get dead-letter queue items."""
    uid = request.user_id
    # TODO: Add admin role check
    try:
        dlq = supabase.table('dead_letter_queue').select('*').order('created_at', desc=True).limit(50).execute().data or []
        return jsonify({"dead_letter": dlq})
    except Exception as e:
        logger.error(f"Dead-letter queue error: {e}")
        return jsonify({"error": "Failed to fetch dead-letter queue"}), 500


@app.route("/api/admin/dead-letter/<job_id>/retry", methods=["POST"])
@login_required
def api_admin_retry_dead_letter(job_id):
    """Retry a dead-letter job."""
    uid = request.user_id
    # TODO: Add admin role check
    try:
        dlq = supabase.table('dead_letter_queue').select('*').eq('id', job_id).execute()
        if not dlq.data:
            return jsonify({"error": "Job not found"}), 404
        
        job = dlq.data[0]
        # TODO: Implement retry logic based on job_type
        supabase.table('dead_letter_queue').update({
            'status': 'retrying',
            'resolved_at': datetime.utcnow().isoformat(),
            'resolved_by': f"admin_{uid}"
        }).eq('id', job_id).execute()
        
        return jsonify({"message": "Job marked for retry"})
    except Exception as e:
        logger.error(f"Retry dead-letter error: {e}")
        return jsonify({"error": "Failed to retry job"}), 500


if __name__ == "__main__":
    if supabase:
        ensure_bucket_exists()
    port = int(os.getenv("PORT", 5000))
    app.run(debug=True, host="0.0.0.0", port=port)