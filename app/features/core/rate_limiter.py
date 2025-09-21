"""
Rate limiting utilities for authentication and sensitive endpoints.
Provides in-memory and Redis-based rate limiting with configurable rules.
"""
import time
import os
from typing import Dict, Optional, Tuple
from datetime import datetime, timedelta
from collections import defaultdict
from fastapi import HTTPException, Request, status
from functools import wraps
import logging

logger = logging.getLogger(__name__)


class InMemoryRateLimiter:
    """
    In-memory rate limiter using sliding window algorithm.
    Suitable for single-instance deployments or development.
    """
    
    def __init__(self):
        # Store: {key: [(timestamp, count), ...]}
        self._store: Dict[str, list] = defaultdict(list)
        self._cleanup_interval = 300  # Clean up old entries every 5 minutes
        self._last_cleanup = time.time()
    
    def _cleanup_old_entries(self):
        """Remove entries older than 1 hour to prevent memory leaks."""
        current_time = time.time()
        if current_time - self._last_cleanup < self._cleanup_interval:
            return
            
        cutoff_time = current_time - 3600  # 1 hour ago
        for key in list(self._store.keys()):
            self._store[key] = [
                (timestamp, count) for timestamp, count in self._store[key]
                if timestamp > cutoff_time
            ]
            if not self._store[key]:
                del self._store[key]
        
        self._last_cleanup = current_time
    
    def is_allowed(self, key: str, limit: int, window_seconds: int) -> Tuple[bool, Dict[str, int]]:
        """
        Check if request is allowed within rate limit.
        
        Args:
            key: Unique identifier for the client (IP, user ID, etc.)
            limit: Maximum number of requests allowed
            window_seconds: Time window in seconds
            
        Returns:
            Tuple of (allowed: bool, info: dict with remaining/reset info)
        """
        self._cleanup_old_entries()
        
        current_time = time.time()
        window_start = current_time - window_seconds
        
        # Filter requests within the current window
        entries = self._store[key]
        entries_in_window = [
            (timestamp, count) for timestamp, count in entries
            if timestamp > window_start
        ]
        
        # Update store with filtered entries
        self._store[key] = entries_in_window
        
        # Count total requests in window
        total_requests = sum(count for _, count in entries_in_window)
        
        # Check if limit exceeded
        if total_requests >= limit:
            remaining_requests = 0
            allowed = False
        else:
            remaining_requests = limit - total_requests
            allowed = True
            # Add current request
            self._store[key].append((current_time, 1))
        
        # Calculate reset time (when oldest entry expires)
        reset_time = int(current_time + window_seconds)
        if entries_in_window:
            oldest_timestamp = min(timestamp for timestamp, _ in entries_in_window)
            reset_time = int(oldest_timestamp + window_seconds)
        
        return allowed, {
            "remaining": remaining_requests,
            "reset": reset_time,
            "total": limit,
            "window": window_seconds
        }


class RateLimitConfig:
    """Rate limiting configuration for different endpoints."""
    
    # Authentication endpoints (stricter limits)
    LOGIN_LIMIT = int(os.getenv("RATE_LIMIT_LOGIN", "5"))  # 5 attempts per 15 minutes
    LOGIN_WINDOW = int(os.getenv("RATE_LIMIT_LOGIN_WINDOW", "900"))  # 15 minutes
    
    REGISTER_LIMIT = int(os.getenv("RATE_LIMIT_REGISTER", "3"))  # 3 registrations per hour
    REGISTER_WINDOW = int(os.getenv("RATE_LIMIT_REGISTER_WINDOW", "3600"))  # 1 hour
    
    REFRESH_LIMIT = int(os.getenv("RATE_LIMIT_REFRESH", "10"))  # 10 refreshes per 5 minutes
    REFRESH_WINDOW = int(os.getenv("RATE_LIMIT_REFRESH_WINDOW", "300"))  # 5 minutes
    
    # General API endpoints
    API_LIMIT = int(os.getenv("RATE_LIMIT_API", "100"))  # 100 requests per minute
    API_WINDOW = int(os.getenv("RATE_LIMIT_API_WINDOW", "60"))  # 1 minute
    
    # Secrets access (very strict)
    SECRETS_LIMIT = int(os.getenv("RATE_LIMIT_SECRETS", "20"))  # 20 per 10 minutes
    SECRETS_WINDOW = int(os.getenv("RATE_LIMIT_SECRETS_WINDOW", "600"))  # 10 minutes


# Global rate limiter instance
_rate_limiter = InMemoryRateLimiter()


def get_client_key(request: Request, user_id: Optional[str] = None) -> str:
    """
    Generate a unique key for rate limiting based on client IP and optional user ID.
    """
    # Get client IP (handle reverse proxy headers)
    client_ip = request.headers.get("X-Forwarded-For", "").split(",")[0].strip()
    if not client_ip:
        client_ip = request.headers.get("X-Real-IP", "")
    if not client_ip:
        client_ip = getattr(request.client, "host", "unknown")
    
    # Combine IP and user ID for authenticated requests
    if user_id:
        return f"user:{user_id}:{client_ip}"
    return f"ip:{client_ip}"


def check_rate_limit(
    key: str,
    limit: int,
    window_seconds: int,
    identifier: str = "request"
) -> Dict[str, int]:
    """
    Check rate limit and raise HTTPException if exceeded.
    
    Args:
        key: Rate limit key
        limit: Request limit
        window_seconds: Time window
        identifier: Description for error message
        
    Returns:
        Dict with rate limit info
        
    Raises:
        HTTPException: If rate limit exceeded
    """
    allowed, info = _rate_limiter.is_allowed(key, limit, window_seconds)
    
    if not allowed:
        logger.warning(f"Rate limit exceeded for {identifier}: key={key}, limit={limit}")
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded for {identifier}. "
                   f"Limit: {limit} requests per {window_seconds} seconds. "
                   f"Try again after {info['reset']} seconds.",
            headers={
                "X-RateLimit-Limit": str(info["total"]),
                "X-RateLimit-Remaining": str(info["remaining"]),
                "X-RateLimit-Reset": str(info["reset"]),
                "X-RateLimit-Window": str(info["window"]),
                "Retry-After": str(window_seconds)
            }
        )
    
    return info


def rate_limit_login(request: Request) -> Dict[str, int]:
    """Rate limit for login endpoints."""
    key = get_client_key(request)
    return check_rate_limit(
        key=f"login:{key}",
        limit=RateLimitConfig.LOGIN_LIMIT,
        window_seconds=RateLimitConfig.LOGIN_WINDOW,
        identifier="login"
    )


def rate_limit_register(request: Request) -> Dict[str, int]:
    """Rate limit for registration endpoints."""
    key = get_client_key(request)
    return check_rate_limit(
        key=f"register:{key}",
        limit=RateLimitConfig.REGISTER_LIMIT,
        window_seconds=RateLimitConfig.REGISTER_WINDOW,
        identifier="registration"
    )


def rate_limit_refresh(request: Request) -> Dict[str, int]:
    """Rate limit for token refresh endpoints."""
    key = get_client_key(request)
    return check_rate_limit(
        key=f"refresh:{key}",
        limit=RateLimitConfig.REFRESH_LIMIT,
        window_seconds=RateLimitConfig.REFRESH_WINDOW,
        identifier="token refresh"
    )


def rate_limit_secrets(request: Request, user_id: str) -> Dict[str, int]:
    """Rate limit for secrets access endpoints."""
    key = get_client_key(request, user_id)
    return check_rate_limit(
        key=f"secrets:{key}",
        limit=RateLimitConfig.SECRETS_LIMIT,
        window_seconds=RateLimitConfig.SECRETS_WINDOW,
        identifier="secrets access"
    )


def rate_limit_api(request: Request, user_id: Optional[str] = None) -> Dict[str, int]:
    """Rate limit for general API endpoints."""
    key = get_client_key(request, user_id)
    return check_rate_limit(
        key=f"api:{key}",
        limit=RateLimitConfig.API_LIMIT,
        window_seconds=RateLimitConfig.API_WINDOW,
        identifier="API"
    )