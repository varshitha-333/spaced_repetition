"""
Improved Cron Job System with:
- Execution locks (database-based)
- Idempotency keys
- Subscription validation
- Metrics collection
- Exponential backoff retries
- Structured logging
- Dead-letter queue support
"""

import time
import uuid
import logging
from datetime import datetime
from functools import wraps
from typing import Optional, Dict, Any
import traceback

logger = logging.getLogger(__name__)


class ExecutionLock:
    """Database-based execution lock to prevent concurrent cron executions."""
    
    def __init__(self, supabase_client, lock_key: str, ttl_seconds: int = 300):
        self.supabase = supabase_client
        self.lock_key = lock_key
        self.ttl_seconds = ttl_seconds
        self.locked = False
    
    def acquire(self) -> bool:
        """Attempt to acquire lock. Returns True if successful."""
        try:
            now = datetime.utcnow().isoformat()
            expires_at = (datetime.utcnow() + 
                        timedelta(seconds=self.ttl_seconds)).isoformat()
            
            # Try to insert a new lock record
            result = self.supabase.table('execution_locks').insert({
                'lock_key': self.lock_key,
                'locked_at': now,
                'expires_at': expires_at
            }).execute()
            
            self.locked = True
            logger.info(f"Lock acquired: {self.lock_key}")
            return True
        except Exception as e:
            # Lock already exists or other error
            logger.warning(f"Failed to acquire lock {self.lock_key}: {e}")
            return False
    
    def release(self):
        """Release the lock."""
        if self.locked:
            try:
                self.supabase.table('execution_locks').delete().eq(
                    'lock_key', self.lock_key
                ).execute()
                self.locked = False
                logger.info(f"Lock released: {self.lock_key}")
            except Exception as e:
                logger.error(f"Failed to release lock {self.lock_key}: {e}")
    
    def __enter__(self):
        return self.acquire()
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.release()


def with_execution_lock(supabase_client, lock_key: str, ttl_seconds: int = 300):
    """Decorator to wrap function with execution lock."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            lock = ExecutionLock(supabase_client, lock_key, ttl_seconds)
            if lock.acquire():
                try:
                    return func(*args, **kwargs)
                finally:
                    lock.release()
            else:
                logger.warning(f"Execution already in progress for {lock_key}")
                return None
        return wrapper
    return decorator


class IdempotencyChecker:
    """Check for duplicate executions using idempotency keys."""
    
    def __init__(self, supabase_client):
        self.supabase = supabase_client
    
    def check_and_record(self, idempotency_key: str, job_type: str) -> bool:
        """
        Check if this idempotency key has been used.
        Returns True if this is a new execution (should proceed).
        Returns False if already executed (should skip).
        """
        try:
            # Check if key exists
            existing = self.supabase.table('idempotency_keys').select(
                '*'
            ).eq('key', idempotency_key).execute()
            
            if existing.data:
                logger.info(f"Duplicate execution prevented: {idempotency_key}")
                return False
            
            # Record this execution
            self.supabase.table('idempotency_keys').insert({
                'key': idempotency_key,
                'job_type': job_type,
                'executed_at': datetime.utcnow().isoformat()
            }).execute()
            
            return True
        except Exception as e:
            logger.error(f"Idempotency check failed: {e}")
            # Fail open - allow execution if check fails
            return True


class MetricsCollector:
    """Collect and record system metrics."""
    
    def __init__(self, supabase_client):
        self.supabase = supabase_client
    
    def record_metric(self, name: str, value: float, unit: str = None, 
                     tags: Dict[str, Any] = None):
        """Record a metric."""
        try:
            self.supabase.table('metrics').insert({
                'metric_name': name,
                'metric_value': value,
                'metric_unit': unit,
                'tags': tags or {},
                'timestamp': datetime.utcnow().isoformat()
            }).execute()
        except Exception as e:
            logger.error(f"Failed to record metric {name}: {e}")
    
    def record_cron_execution(self, execution_id: str, job_type: str, 
                            status: str, processed: int = 0, 
                            skipped: int = 0, failed: int = 0,
                            duration_ms: int = None, 
                            error_message: str = None,
                            idempotency_key: str = None):
        """Record a cron job execution."""
        try:
            self.supabase.table('cron_executions').insert({
                'execution_id': execution_id,
                'job_type': job_type,
                'status': status,
                'started_at': datetime.utcnow().isoformat(),
                'completed_at': datetime.utcnow().isoformat() if status != 'started' else None,
                'duration_ms': duration_ms,
                'processed_count': processed,
                'skipped_count': skipped,
                'failed_count': failed,
                'error_message': error_message,
                'idempotency_key': idempotency_key
            }).execute()
        except Exception as e:
            logger.error(f"Failed to record cron execution: {e}")


class DeadLetterQueue:
    """Handle permanently failed jobs."""
    
    def __init__(self, supabase_client):
        self.supabase = supabase_client
    
    def add_failed_job(self, job_type: str, job_id: str, user_id: str,
                      payload: Dict[str, Any], error_message: str,
                      error_stack: str, retry_count: int = 0,
                      max_retries: int = 3):
        """Add a failed job to the dead-letter queue."""
        try:
            self.supabase.table('dead_letter_queue').insert({
                'job_type': job_type,
                'job_id': job_id,
                'user_id': user_id,
                'payload': payload,
                'error_message': error_message,
                'error_stack': error_stack,
                'retry_count': retry_count,
                'max_retries': max_retries,
                'status': 'failed'
            }).execute()
            logger.warning(f"Added to dead-letter queue: {job_type}/{job_id}")
        except Exception as e:
            logger.error(f"Failed to add to dead-letter queue: {e}")


def exponential_backoff_retry(func, max_retries: int = 3, 
                             base_delay: float = 1.0):
    """
    Retry function with exponential backoff.
    Returns (success: bool, result: Any, attempts: int)
    """
    for attempt in range(max_retries):
        try:
            result = func()
            return True, result, attempt + 1
        except Exception as e:
            if attempt == max_retries - 1:
                return False, None, attempt + 1
            
            delay = base_delay * (2 ** attempt)
            logger.warning(f"Retry {attempt + 1}/{max_retries} after {delay}s: {e}")
            time.sleep(delay)
    
    return False, None, max_retries


def validate_subscription(supabase_client, user_id: str) -> bool:
    """Check if user has active premium subscription."""
    try:
        result = supabase_client.table('user_state').select(
            'premium_expires_at'
        ).eq('user_id', user_id).execute()
        
        if not result.data:
            return False
        
        expires_at = result.data[0].get('premium_expires_at')
        if not expires_at:
            return False
        
        # Check if subscription is still valid
        expiry_date = datetime.fromisoformat(expires_at)
        return expiry_date > datetime.utcnow()
    except Exception as e:
        logger.error(f"Subscription validation failed: {e}")
        return False


def structured_log(level: str, message: str, **kwargs):
    """Log structured data."""
    log_data = {
        'timestamp': datetime.utcnow().isoformat(),
        'level': level,
        'message': message,
        **kwargs
    }
    
    log_func = getattr(logger, level.lower(), logger.info)
    log_func(f"{message} | Context: {kwargs}")
