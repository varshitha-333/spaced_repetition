"""
LearnFlow Premium Routes
-------------------------
Drop-in Flask Blueprint that adds:
  • 30-day Premium coupon flow (LAUNCH30, STUDENT30, FIRST100, LEARNFREE)
  • Premium status check
  • Twilio SMS toggle (real if env vars present, else mock-logs)
  • Reviews submission + Gemini-scored Top-5 reviews
  • Premium AI features (Smart Summary, Flashcards, Quiz Me, Concept Linker, Streak Coach)

How to register in app.py
-------------------------
    from premium_routes import premium_bp, init_premium
    init_premium(app, supabase, logger, decode_token)
    app.register_blueprint(premium_bp)

The blueprint expects two Supabase tables (SQL at the bottom of this file).
"""

from __future__ import annotations

import os
import json
import logging
import random
import string
from datetime import datetime, timedelta, timezone
from functools import wraps

import requests
from flask import Blueprint, request, jsonify

premium_bp = Blueprint("premium", __name__)

# Filled in by init_premium()
_supabase = None
_logger: logging.Logger = logging.getLogger("premium")
_decode_token = None

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
VALID_COUPONS = {"LAUNCH30", "STUDENT30", "FIRST100", "LEARNFREE"}
PREMIUM_DAYS = 30
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
GEMINI_URL = (
    f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"
)

TWILIO_SID = os.getenv("TWILIO_ACCOUNT_SID", "")
TWILIO_TOKEN = os.getenv("TWILIO_AUTH_TOKEN", "")
TWILIO_FROM = os.getenv("TWILIO_FROM_NUMBER", "")


def init_premium(app, supabase_client, logger, decode_token_fn):
    """Wire shared dependencies from app.py into this blueprint."""
    global _supabase, _logger, _decode_token
    _supabase = supabase_client
    _logger = logger
    _decode_token = decode_token_fn
    _logger.info("[PREMIUM] Blueprint initialized.")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _auth_user():
    """Decode bearer token → user dict {id, username}. Returns None if invalid."""
    auth = request.headers.get("Authorization", "")
    token = auth.removeprefix("Bearer ").strip()
    if not token or _decode_token is None:
        return None
    try:
        data = _decode_token(token)
        return {"id": data["user_id"], "username": data.get("username", "")}
    except Exception:
        return None


def require_auth(f):
    @wraps(f)
    def w(*a, **kw):
        u = _auth_user()
        if not u:
            return jsonify({"error": "unauthorized"}), 401
        request.current_user = u
        return f(*a, **kw)
    return w


def _get_premium_state(user_id: str) -> dict:
    """Return {is_premium, expires_at_iso, days_left}."""
    try:
        r = _supabase.table("user_state").select("premium_expires_at").eq("user_id", user_id).execute()
        if not r.data:
            return {"is_premium": False, "expires_at": None, "days_left": 0}
        exp = r.data[0].get("premium_expires_at")
        if not exp:
            return {"is_premium": False, "expires_at": None, "days_left": 0}
        exp_dt = datetime.fromisoformat(exp.replace("Z", "+00:00"))
        now = datetime.now(timezone.utc)
        if exp_dt <= now:
            return {"is_premium": False, "expires_at": exp, "days_left": 0}
        days_left = max(0, (exp_dt - now).days + 1)
        return {"is_premium": True, "expires_at": exp, "days_left": days_left}
    except Exception as e:
        _logger.warning(f"[PREMIUM] state lookup failed: {e}")
        return {"is_premium": False, "expires_at": None, "days_left": 0}


def _gemini_generate(prompt: str, system: str | None = None) -> str:
    """Call Gemini. Returns text content, or empty string on failure."""
    if not GEMINI_API_KEY:
        _logger.info("[GEMINI] no API key — returning stub response")
        return ""
    body = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.6, "maxOutputTokens": 1024},
    }
    if system:
        body["systemInstruction"] = {"parts": [{"text": system}]}
    try:
        resp = requests.post(
            GEMINI_URL,
            params={"key": GEMINI_API_KEY},
            json=body,
            timeout=25,
        )
        if resp.status_code != 200:
            _logger.warning(f"[GEMINI] {resp.status_code}: {resp.text[:200]}")
            return ""
        data = resp.json()
        return (
            data.get("candidates", [{}])[0]
            .get("content", {})
            .get("parts", [{}])[0]
            .get("text", "")
        )
    except Exception as e:
        _logger.warning(f"[GEMINI] error: {e}")
        return ""


def _send_sms_real_or_mock(to_phone: str, body: str) -> dict:
    """Try real Twilio if creds present, else mock-log."""
    if TWILIO_SID and TWILIO_TOKEN and TWILIO_FROM:
        try:
            from twilio.rest import Client
            client = Client(TWILIO_SID, TWILIO_TOKEN)
            msg = client.messages.create(body=body, from_=TWILIO_FROM, to=to_phone)
            _logger.info(f"[SMS REAL] sid={msg.sid} to={to_phone}")
            return {"mode": "real", "sid": msg.sid}
        except Exception as e:
            _logger.warning(f"[SMS REAL FAIL] {e} — falling back to mock")
    _logger.info(f"[SMS MOCK] to={to_phone} body={body!r}")
    return {"mode": "mock", "to": to_phone, "body": body}


# ---------------------------------------------------------------------------
# Premium status
# ---------------------------------------------------------------------------
@premium_bp.route("/api/premium/status")
@require_auth
def premium_status():
    u = request.current_user
    st = _get_premium_state(u["id"])
    return jsonify({
        "is_premium": st["is_premium"],
        "expires_at": st["expires_at"],
        "days_left": st["days_left"],
        "campaign_active": True,  # 30-day launch campaign flag
    })


# ---------------------------------------------------------------------------
# Coupon redemption (dummy payment page)
# ---------------------------------------------------------------------------
@premium_bp.route("/api/premium/redeem", methods=["POST"])
@require_auth
def premium_redeem():
    """
    Body: { name, email, phone, coupon }
    Validates coupon (case-insensitive). Stores dummy 'payment' record.
    Sets premium_expires_at = now + 30 days. Returns receipt.
    """
    u = request.current_user
    data = request.get_json(silent=True) or {}
    coupon_raw = (data.get("coupon") or "").strip().upper()
    if coupon_raw not in VALID_COUPONS:
        return jsonify({"error": "invalid_coupon", "valid": sorted(VALID_COUPONS)}), 400

    name = (data.get("name") or "").strip()[:80]
    email = (data.get("email") or "").strip()[:120]
    phone = (data.get("phone") or "").strip()[:20]
    if not name or not email:
        return jsonify({"error": "missing_fields"}), 400

    now = datetime.now(timezone.utc)
    expires = now + timedelta(days=PREMIUM_DAYS)

    try:
        _supabase.table("user_state").update({
            "premium_expires_at": expires.isoformat(),
            "premium_coupon": coupon_raw,
            "premium_redeemed_at": now.isoformat(),
            "premium_billing_name": name,
            "premium_billing_email": email,
        }).eq("user_id", u["id"]).execute()
    except Exception as e:
        _logger.error(f"[REDEEM] update failed: {e}")
        return jsonify({"error": "db_error"}), 500

    receipt_id = "LF-" + "".join(random.choices(string.ascii_uppercase + string.digits, k=8))
    return jsonify({
        "ok": True,
        "receipt": {
            "id": receipt_id,
            "coupon": coupon_raw,
            "name": name,
            "email": email,
            "phone": phone,
            "original_price_inr": 499,
            "discount_inr": 499,
            "final_price_inr": 0,
            "plan": "Premium",
            "duration_days": PREMIUM_DAYS,
            "expires_at": expires.isoformat(),
            "issued_at": now.isoformat(),
        },
        "premium": {
            "is_premium": True,
            "expires_at": expires.isoformat(),
            "days_left": PREMIUM_DAYS,
        },
    })


# ---------------------------------------------------------------------------
# SMS notifications
# ---------------------------------------------------------------------------
@premium_bp.route("/api/sms/enable", methods=["POST"])
@require_auth
def sms_enable():
    """
    Body: { phone, enabled }
    Saves user's phone + enabled flag. Schedule is fixed: 8 AM + 9 PM local.
    """
    u = request.current_user
    data = request.get_json(silent=True) or {}
    phone = (data.get("phone") or "").strip()
    enabled = bool(data.get("enabled", True))
    if enabled and not phone:
        return jsonify({"error": "phone_required"}), 400

    try:
        _supabase.table("user_state").update({
            "notification_phone": phone,
            "sms_notifications_enabled": enabled,
            "sms_morning_hour": 8,
            "sms_night_hour": 21,
        }).eq("user_id", u["id"]).execute()
    except Exception as e:
        _logger.error(f"[SMS ENABLE] {e}")
        return jsonify({"error": "db_error"}), 500

    # Send a confirmation SMS immediately
    if enabled:
        body = (
            f"🎉 LearnFlow SMS reminders enabled!\n"
            f"You'll get a morning nudge at 8 AM and a night recap at 9 PM. "
            f"Reply STOP to opt out anytime."
        )
        result = _send_sms_real_or_mock(phone, body)
    else:
        result = {"mode": "disabled"}

    return jsonify({"ok": True, "sms": result, "schedule": {"morning_hour": 8, "night_hour": 21}})


@premium_bp.route("/api/sms/test", methods=["POST"])
@require_auth
def sms_test():
    """Send a one-off test SMS to the saved phone."""
    u = request.current_user
    r = _supabase.table("user_state").select("notification_phone").eq("user_id", u["id"]).execute()
    phone = (r.data[0].get("notification_phone") if r.data else "") or ""
    if not phone:
        return jsonify({"error": "no_phone"}), 400
    body = "📚 LearnFlow test SMS — your reminders are working. Keep that streak alive!"
    result = _send_sms_real_or_mock(phone, body)
    return jsonify({"ok": True, "sms": result})


@premium_bp.route("/api/sms/cron/<slot>", methods=["POST"])
def sms_cron(slot):
    """
    Public cron-style endpoint (call from external scheduler, e.g. cron-job.org).
    slot = 'morning' or 'night'.
    Iterates all users with sms_notifications_enabled=True.
    """
    if slot not in ("morning", "night"):
        return jsonify({"error": "bad_slot"}), 400
    if request.headers.get("X-Cron-Secret") != os.getenv("CRON_SECRET", "learnflow"):
        return jsonify({"error": "forbidden"}), 403

    try:
        users = _supabase.table("user_state").select(
            "user_id,notification_phone,sms_notifications_enabled"
        ).eq("sms_notifications_enabled", True).execute().data or []
    except Exception as e:
        return jsonify({"error": f"db: {e}"}), 500

    sent = []
    for row in users:
        phone = row.get("notification_phone") or ""
        if not phone:
            continue
        if slot == "morning":
            body = (
                "🌅 Good morning! Time for today's spaced revisions on LearnFlow. "
                "Open the app to see what's due — small wins compound."
            )
        else:
            body = (
                "🌙 Night check-in: how did today go? "
                "Mark your revisions complete on LearnFlow — your streak is watching you. ✨"
            )
        r = _send_sms_real_or_mock(phone, body)
        sent.append({"user_id": row["user_id"], "result": r})

    return jsonify({"ok": True, "slot": slot, "count": len(sent), "sent": sent})


# ---------------------------------------------------------------------------
# Reviews + Gemini scoring
# ---------------------------------------------------------------------------
@premium_bp.route("/api/reviews", methods=["POST"])
@require_auth
def reviews_submit():
    u = request.current_user
    data = request.get_json(silent=True) or {}
    rating = int(data.get("rating") or 0)
    text = (data.get("text") or "").strip()
    name = (data.get("name") or u["username"] or "Anonymous")[:60]
    if rating < 1 or rating > 5:
        return jsonify({"error": "rating_1_to_5"}), 400
    if len(text) < 10:
        return jsonify({"error": "review_too_short"}), 400

    # Ask Gemini to score the review's quality (clarity + sentiment + specificity)
    score_text = _gemini_generate(
        f"Rate this product review on a 0-10 scale for: clarity, helpfulness, "
        f"and specificity. Return ONLY the number, nothing else.\n\nReview: {text}",
        system="You are a strict review-quality grader. Output a single integer 0-10.",
    )
    quality = 6
    try:
        quality = max(0, min(10, int("".join(ch for ch in score_text if ch.isdigit())[:2] or "6")))
    except Exception:
        quality = 6

    try:
        _supabase.table("reviews").insert({
            "user_id": u["id"],
            "name": name,
            "rating": rating,
            "text": text,
            "quality_score": quality,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }).execute()
    except Exception as e:
        _logger.error(f"[REVIEW] insert failed: {e}")
        return jsonify({"error": "db_error"}), 500

    return jsonify({"ok": True, "quality_score": quality})


@premium_bp.route("/api/reviews/top")
def reviews_top():
    """Public — top 5 reviews ranked by Gemini quality_score then rating."""
    try:
        r = _supabase.table("reviews").select(
            "name,rating,text,quality_score,created_at"
        ).order("quality_score", desc=True).order("rating", desc=True).limit(5).execute()
        return jsonify({"reviews": r.data or []})
    except Exception as e:
        _logger.warning(f"[REVIEW TOP] {e}")
        return jsonify({"reviews": []})


# ---------------------------------------------------------------------------
# Profile
# ---------------------------------------------------------------------------
@premium_bp.route("/api/profile", methods=["GET", "PUT"])
@require_auth
def profile():
    u = request.current_user
    if request.method == "GET":
        r = _supabase.table("user_state").select(
            "notification_phone,sms_notifications_enabled,premium_expires_at,"
            "premium_billing_name,premium_billing_email,drive_connected"
        ).eq("user_id", u["id"]).execute()
        row = (r.data or [{}])[0]
        st = _get_premium_state(u["id"])
        return jsonify({
            "username": u["username"],
            "phone": row.get("notification_phone"),
            "sms_enabled": bool(row.get("sms_notifications_enabled")),
            "display_name": row.get("premium_billing_name") or u["username"],
            "email": row.get("premium_billing_email"),
            "drive_connected": bool(row.get("drive_connected")),
            "premium": st,
        })

    # PUT
    data = request.get_json(silent=True) or {}
    update = {}
    for src, dst in [
        ("display_name", "premium_billing_name"),
        ("email", "premium_billing_email"),
        ("phone", "notification_phone"),
    ]:
        if src in data and data[src] is not None:
            update[dst] = str(data[src])[:120]
    if "sms_enabled" in data:
        update["sms_notifications_enabled"] = bool(data["sms_enabled"])
    if not update:
        return jsonify({"ok": True, "noop": True})
    try:
        _supabase.table("user_state").update(update).eq("user_id", u["id"]).execute()
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    return jsonify({"ok": True, "updated": list(update.keys())})


# ---------------------------------------------------------------------------
# Premium AI features
# ---------------------------------------------------------------------------
def _require_premium():
    u = request.current_user
    st = _get_premium_state(u["id"])
    if not st["is_premium"]:
        return None, (jsonify({"error": "premium_required"}), 402)
    return u, None


@premium_bp.route("/api/ai/summary", methods=["POST"])
@require_auth
def ai_summary():
    _, err = _require_premium()
    if err:
        return err
    text = (request.get_json(silent=True) or {}).get("text", "")[:8000]
    if len(text) < 30:
        return jsonify({"error": "text_too_short"}), 400
    out = _gemini_generate(
        f"Summarize the following study material in 5 bullet points a student can "
        f"actually remember. Each bullet ≤ 18 words. Plain text, no markdown.\n\n{text}",
        system="You are a study-buddy that produces tight, memorable summaries.",
    )
    return jsonify({"summary": out or "• (Gemini key not set — set GEMINI_API_KEY to enable)"})


@premium_bp.route("/api/ai/flashcards", methods=["POST"])
@require_auth
def ai_flashcards():
    _, err = _require_premium()
    if err:
        return err
    text = (request.get_json(silent=True) or {}).get("text", "")[:8000]
    if len(text) < 30:
        return jsonify({"error": "text_too_short"}), 400
    out = _gemini_generate(
        f"Create 6 flashcards from this material. Return STRICT JSON array of "
        f'objects: [{{"q":"...","a":"..."}}]. No commentary.\n\n{text}',
        system="You are a flashcard generator. Output strict JSON only.",
    )
    cards = []
    try:
        start = out.find("[")
        end = out.rfind("]")
        if start != -1 and end != -1:
            cards = json.loads(out[start:end + 1])
    except Exception:
        cards = []
    if not cards:
        cards = [{"q": "Set GEMINI_API_KEY to generate real flashcards", "a": "👨‍💻"}]
    return jsonify({"flashcards": cards[:6]})


@premium_bp.route("/api/ai/quiz", methods=["POST"])
@require_auth
def ai_quiz():
    _, err = _require_premium()
    if err:
        return err
    text = (request.get_json(silent=True) or {}).get("text", "")[:8000]
    if len(text) < 30:
        return jsonify({"error": "text_too_short"}), 400
    out = _gemini_generate(
        f"Create 5 multiple-choice questions from this material. STRICT JSON: "
        f'[{{"q":"...","options":["A","B","C","D"],"answer_index":0,"why":"..."}}].\n\n{text}',
        system="You are a quiz generator. JSON only.",
    )
    items = []
    try:
        start = out.find("[")
        end = out.rfind("]")
        if start != -1 and end != -1:
            items = json.loads(out[start:end + 1])
    except Exception:
        items = []
    if not items:
        items = [{
            "q": "Set GEMINI_API_KEY to enable real quizzes",
            "options": ["OK", "Sure", "Got it", "👍"],
            "answer_index": 3,
            "why": "Demo placeholder.",
        }]
    return jsonify({"quiz": items[:5]})


@premium_bp.route("/api/ai/concepts", methods=["POST"])
@require_auth
def ai_concepts():
    """Concept Linker — given list of resource titles, return clusters."""
    _, err = _require_premium()
    if err:
        return err
    titles = (request.get_json(silent=True) or {}).get("titles", [])[:80]
    if not titles:
        return jsonify({"clusters": []})
    out = _gemini_generate(
        f"Group these study resource titles into 3-6 concept clusters. STRICT JSON: "
        f'[{{"concept":"...","items":["title1","title2"]}}].\n\nTitles:\n'
        + "\n".join(f"- {t}" for t in titles),
        system="You are a concept-mapper. JSON only.",
    )
    clusters = []
    try:
        start = out.find("[")
        end = out.rfind("]")
        if start != -1 and end != -1:
            clusters = json.loads(out[start:end + 1])
    except Exception:
        clusters = []
    if not clusters:
        # Fallback: bucket by first letter
        buckets: dict = {}
        for t in titles:
            k = (t[:1] or "?").upper()
            buckets.setdefault(k, []).append(t)
        clusters = [{"concept": f"Starts with “{k}”", "items": v} for k, v in buckets.items()]
    return jsonify({"clusters": clusters[:6]})


@premium_bp.route("/api/ai/streak-coach", methods=["POST"])
@require_auth
def ai_streak_coach():
    _, err = _require_premium()
    if err:
        return err
    data = request.get_json(silent=True) or {}
    streak = int(data.get("streak", 0))
    done = int(data.get("done_today", 0))
    due = int(data.get("due_today", 0))
    out = _gemini_generate(
        f"Write ONE motivating sentence (≤ 22 words) for a student. "
        f"Streak: {streak} days. Completed today: {done}. Still due: {due}. "
        f"Be specific, warm, no emojis at start.",
        system="You are a calm, kind study coach.",
    )
    if not out:
        out = (
            f"You're {streak} days strong — finish the last {due} revisions and own tonight."
            if due else f"{streak}-day streak and a clean slate. That's how mastery is built."
        )
    return jsonify({"message": out.strip()})


# ---------------------------------------------------------------------------
# SQL SCHEMA (run once in Supabase SQL editor)
# ---------------------------------------------------------------------------
SCHEMA_SQL = """
-- New columns on user_state
ALTER TABLE user_state ADD COLUMN IF NOT EXISTS premium_expires_at timestamptz;
ALTER TABLE user_state ADD COLUMN IF NOT EXISTS premium_coupon text;
ALTER TABLE user_state ADD COLUMN IF NOT EXISTS premium_redeemed_at timestamptz;
ALTER TABLE user_state ADD COLUMN IF NOT EXISTS premium_billing_name text;
ALTER TABLE user_state ADD COLUMN IF NOT EXISTS premium_billing_email text;
ALTER TABLE user_state ADD COLUMN IF NOT EXISTS sms_morning_hour int DEFAULT 8;
ALTER TABLE user_state ADD COLUMN IF NOT EXISTS sms_night_hour int DEFAULT 21;

-- Reviews table
CREATE TABLE IF NOT EXISTS reviews (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id uuid NOT NULL,
    name text NOT NULL,
    rating int NOT NULL CHECK (rating BETWEEN 1 AND 5),
    text text NOT NULL,
    quality_score int DEFAULT 5,
    created_at timestamptz DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_reviews_quality ON reviews (quality_score DESC, rating DESC);
"""
