"""
Shared rate limiter to coordinate OpenAI API retries across all components.
Prevents thundering herd when multiple threads/components hit rate limits simultaneously.
"""

import threading
import time

# Global rate limiter state
_rate_limit_lock = threading.Lock()
_last_rate_limit_time = 0
_rate_limit_backoff = 0


def wait_if_rate_limited():
    """
    Check if we need to wait due to a recent rate limit.
    Returns True if we waited, False otherwise.
    """
    global _last_rate_limit_time, _rate_limit_backoff
    
    current_time = time.time()
    waited = False
    
    with _rate_limit_lock:
        # If another thread/component recently hit a rate limit, wait
        if _rate_limit_backoff > 0 and current_time < _last_rate_limit_time + _rate_limit_backoff:
            wait_time = (_last_rate_limit_time + _rate_limit_backoff) - current_time
            if wait_time > 0:
                waited = True
    
    if waited:
        time.sleep(wait_time)
    
    return waited


def record_rate_limit(delay: float):
    """
    Record that a rate limit was hit and update the global backoff.
    Other threads/components will wait before making new requests.
    
    Args:
        delay: The delay we're using for this retry attempt
    """
    global _last_rate_limit_time, _rate_limit_backoff
    
    with _rate_limit_lock:
        _last_rate_limit_time = time.time()
        # Use longer backoff to give API time to recover
        _rate_limit_backoff = max(_rate_limit_backoff, delay * 2)


def clear_rate_limit_if_expired():
    """
    Clear the global backoff if enough time has passed.
    Call this after a successful request.
    """
    global _rate_limit_backoff
    
    current_time = time.time()
    with _rate_limit_lock:
        if current_time > _last_rate_limit_time + _rate_limit_backoff:
            _rate_limit_backoff = 0
