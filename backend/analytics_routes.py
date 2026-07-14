"""
Analytics Routes
Provides comprehensive student learning analytics
"""

import logging
from datetime import datetime, timedelta, date
from flask import Blueprint, request, jsonify
from functools import wraps

analytics_bp = Blueprint('analytics', __name__)
_logger = logging.getLogger("analytics")

# Will be set by init_analytics
_supabase = None
_decode_token = None


def init_analytics(supabase_client, decode_token_fn):
    """Wire shared dependencies from app.py into this blueprint."""
    global _supabase, _decode_token
    _supabase = supabase_client
    _decode_token = decode_token_fn
    _logger.info("[ANALYTICS] Blueprint initialized.")


def require_auth(f):
    """Decorator to require authentication."""
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({"error": "Unauthorized"}), 401
        
        token = auth_header.split(' ')[1]
        user_id = _decode_token(token)
        if not user_id:
            return jsonify({"error": "Invalid token"}), 401
        
        request.user_id = user_id
        return f(*args, **kwargs)
    return decorated


@analytics_bp.route("/api/analytics/overview", methods=["GET"])
@require_auth
def analytics_overview():
    """Get overall learning statistics."""
    uid = request.user_id
    try:
        # Get learnings count
        learnings = _supabase.table('learnings').select('*').eq('user_id', uid).execute().data or []
        
        # Get revisions count
        revisions = _supabase.table('revisions').select('*').eq('user_id', uid).execute().data or []
        
        # Get AI artifacts count - efficient query using learning IDs
        learning_ids = [l['id'] for l in learnings]
        user_ai_artifacts = []
        if learning_ids:
            ai_artifacts = _supabase.table('ai_artifacts').select('*').in_('learning_id', learning_ids).execute().data or []
            user_ai_artifacts = ai_artifacts
        
        # Count by artifact type
        flashcards = len([a for a in user_ai_artifacts if a.get('artifact_type') == 'flashcards'])
        quizzes = len([a for a in user_ai_artifacts if a.get('artifact_type') == 'quiz'])
        mindmaps = len([a for a in user_ai_artifacts if a.get('artifact_type') == 'mindmap'])
        keywords = len([a for a in user_ai_artifacts if a.get('artifact_type') == 'keywords'])
        summaries = len([a for a in user_ai_artifacts if a.get('artifact_type') == 'summary'])
        revision_notes = len([a for a in user_ai_artifacts if a.get('artifact_type') == 'revision_notes'])
        
        # Revision status
        completed_revisions = len([r for r in revisions if r.get('completed')])
        pending_revisions = len([r for r in revisions if not r.get('completed')])
        
        today = date.today().isoformat()
        overdue_revisions = len([r for r in revisions if r.get('scheduled_date') < today and not r.get('completed')])
        today_revisions = len([r for r in revisions if r.get('scheduled_date') == today])
        
        # Get user state for streak
        user_state = _supabase.table('user_state').select('*').eq('user_id', uid).execute().data or []
        current_streak = user_state[0].get('current_streak', 0) if user_state else 0
        
        return jsonify({
            "total_study_materials": len(learnings),
            "total_revision_materials": len(revisions),
            "total_ai_materials": len(user_ai_artifacts),
            "total_flashcards": flashcards,
            "total_quiz_questions": quizzes,
            "total_mindmaps": mindmaps,
            "total_keywords": keywords,
            "total_summaries": summaries,
            "total_revision_notes": revision_notes,
            "total_completed_revisions": completed_revisions,
            "total_pending_revisions": pending_revisions,
            "total_missed_revisions": overdue_revisions,
            "total_upcoming_revisions": today_revisions,
            "current_streak": current_streak
        })
    except Exception as e:
        _logger.error(f"[ANALYTICS OVERVIEW] error: {e}")
        return jsonify({"error": str(e)}), 500


@analytics_bp.route("/api/analytics/revision-progress", methods=["GET"])
@require_auth
def revision_progress():
    """Get revision progress statistics."""
    uid = request.user_id
    try:
        revisions = _supabase.table('revisions').select('*').eq('user_id', uid).execute().data or []
        
        if not revisions:
            return jsonify({
                "overall_completion": 0,
                "remaining": 100,
                "by_stage": {}
            })
        
        total = len(revisions)
        completed = len([r for r in revisions if r.get('completed')])
        completion_percent = round((completed / total) * 100, 1) if total > 0 else 0
        
        # Progress by stage
        by_stage = {}
        for stage in [1, 4, 7, 30, 180]:
            stage_revisions = [r for r in revisions if r.get('stage') == stage]
            stage_total = len(stage_revisions)
            stage_completed = len([r for r in stage_revisions if r.get('completed')])
            by_stage[f"day_{stage}"] = {
                "total": stage_total,
                "completed": stage_completed,
                "pending": stage_total - stage_completed,
                "completion_percent": round((stage_completed / stage_total) * 100, 1) if stage_total > 0 else 0
            }
        
        return jsonify({
            "overall_completion": completion_percent,
            "remaining": round(100 - completion_percent, 1),
            "by_stage": by_stage
        })
    except Exception as e:
        _logger.error(f"[REVISION PROGRESS] error: {e}")
        return jsonify({"error": str(e)}), 500


@analytics_bp.route("/api/analytics/today", methods=["GET"])
@require_auth
def today_analytics():
    """Get today's revision analytics."""
    uid = request.user_id
    try:
        today = date.today().isoformat()
        revisions = _supabase.table('revisions').select('*').eq('user_id', uid).execute().data or []
        
        today_revisions = [r for r in revisions if r.get('scheduled_date') == today]
        completed_today = len([r for r in today_revisions if r.get('completed')])
        pending_today = len([r for r in today_revisions if not r.get('completed')])
        
        # Calculate average completion time (mock - would need actual timing data)
        avg_completion_time = 25  # minutes (placeholder)
        
        return jsonify({
            "today_revision_count": len(today_revisions),
            "completed_today": completed_today,
            "pending_today": pending_today,
            "missed_today": 0,  # Would be calculated at end of day
            "avg_completion_time": avg_completion_time
        })
    except Exception as e:
        _logger.error(f"[TODAY ANALYTICS] error: {e}")
        return jsonify({"error": str(e)}), 500


@analytics_bp.route("/api/analytics/streak", methods=["GET"])
@require_auth
def streak_analytics():
    """Get learning streak analytics."""
    uid = request.user_id
    try:
        user_state = _supabase.table('user_state').select('*').eq('user_id', uid).execute().data or []
        
        if not user_state:
            return jsonify({
                "current_streak": 0,
                "longest_streak": 0,
                "days_studied": 0,
                "days_missed": 0,
                "consistency_score": 0
            })
        
        state = user_state[0]
        current_streak = state.get('current_streak', 0)
        
        # Calculate days studied (mock - would need actual completion history)
        days_studied = current_streak  # placeholder
        days_missed = 0  # placeholder
        consistency_score = min(100, current_streak * 5)  # placeholder calculation
        
        return jsonify({
            "current_streak": current_streak,
            "longest_streak": current_streak,  # Would track max streak
            "days_studied": days_studied,
            "days_missed": days_missed,
            "consistency_score": consistency_score
        })
    except Exception as e:
        _logger.error(f"[STREAK ANALYTICS] error: {e}")
        return jsonify({"error": str(e)}), 500


@analytics_bp.route("/api/analytics/completion-history", methods=["GET"])
@require_auth
def completion_history():
    """Get completion history for graphs."""
    uid = request.user_id
    try:
        revisions = _supabase.table('revisions').select('*').eq('user_id', uid).execute().data or []
        
        # Group by date
        daily_counts = {}
        for r in revisions:
            if r.get('completed_date'):
                completed_date = r.get('completed_date')[:10]  # YYYY-MM-DD
                daily_counts[completed_date] = daily_counts.get(completed_date, 0) + 1
        
        # Get last 30 days
        daily_history = []
        for i in range(30):
            d = (date.today() - timedelta(days=i)).isoformat()
            daily_history.append({
                "date": d,
                "count": daily_counts.get(d, 0)
            })
        
        daily_history.reverse()
        
        return jsonify({
            "daily_history": daily_history,
            "weekly_history": [],  # Would aggregate daily
            "monthly_history": []  # Would aggregate weekly
        })
    except Exception as e:
        _logger.error(f"[COMPLETION HISTORY] error: {e}")
        return jsonify({"error": str(e)}), 500


@analytics_bp.route("/api/analytics/sms-status", methods=["GET"])
@require_auth
def sms_status():
    """Get SMS reminder status."""
    uid = request.user_id
    try:
        user_state = _supabase.table('user_state').select('*').eq('user_id', uid).execute().data or []
        
        if not user_state:
            return jsonify({
                "phone_number": None,
                "sms_enabled": False,
                "last_reminder_sent": None,
                "next_reminder_scheduled": None,
                "total_sms_sent": 0,
                "last_delivery_status": None,
                "last_failure_reason": None
            })
        
        state = user_state[0]
        
        return jsonify({
            "phone_number": state.get('notification_phone'),
            "sms_enabled": bool(state.get('sms_notifications_enabled')),
            "last_reminder_sent": state.get('last_sms_sent_date'),
            "next_reminder_scheduled": None,  # Would calculate based on schedule
            "total_sms_sent": 0,  # Would track in metrics
            "last_delivery_status": None,  # Would track from Twilio webhooks
            "last_failure_reason": None
        })
    except Exception as e:
        _logger.error(f"[SMS STATUS] error: {e}")
        return jsonify({"error": str(e)}), 500
