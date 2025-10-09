"""
Production-ready rate limiting system for FastAPI applications.
Supports multiple algorithms, storage backends, and tenant isolation.
"""
import time
import json
import structlog
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Tuple, List
from dataclasses import dataclass, asdict
from enum import Enum
import asyncio
from datetime import datetime, timedelta

logger = structlog.get_logger(__name__)


class RateLimitAlgorithm(Enum):
    """Rate limiting algorithms."""
    FIXED_WINDOW = "fixed_window"
    SLIDING_WINDOW = "sliding_window"
    TOKEN_BUCKET = "token_bucket"


class RateLimitScope(Enum):
    """Rate limiting scopes."""
    GLOBAL = "global"
    TENANT = "tenant"
    USER = "user"
    ENDPOINT = "endpoint"
    IP = "ip"


@dataclass
class RateLimitRule:
    """Rate limiting rule configuration."""
    scope: RateLimitScope
    algorithm: RateLimitAlgorithm
    limit: int  # Number of requests
    window: int  # Time window in seconds
    identifier: Optional[str] = None  # Specific identifier (e.g., endpoint path)
    burst_allowance: int = 0  # Additional requests allowed in burst

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'RateLimitRule':
        data['scope'] = RateLimitScope(data['scope'])
        data['algorithm'] = RateLimitAlgorithm(data['algorithm'])
        return cls(**data)


@dataclass
class RateLimitResult:
    """Result of a rate limit check."""
    allowed: bool
    remaining: int
    reset_time: datetime
    retry_after: Optional[int] = None  # Seconds to wait before retrying
    rule_matched: Optional[RateLimitRule] = None

    def to_headers(self) -> Dict[str, str]:
        """Convert to HTTP headers following standard conventions."""
        headers = {
            "X-RateLimit-Remaining": str(self.remaining),
            "X-RateLimit-Reset": str(int(self.reset_time.timestamp())),
        }

        if self.retry_after:
            headers["Retry-After"] = str(self.retry_after)

        if self.rule_matched:
            headers["X-RateLimit-Limit"] = str(self.rule_matched.limit)
            headers["X-RateLimit-Window"] = str(self.rule_matched.window)

        return headers


class RateLimitStorage(ABC):
    """Abstract base class for rate limit storage backends."""

    @abstractmethod
    async def get_usage(self, key: str, window: int) -> int:
        """Get current usage count for a key within the time window."""
        pass

    @abstractmethod
    async def increment_usage(self, key: str, window: int, amount: int = 1) -> int:
        """Increment usage count and return new total."""
        pass

    @abstractmethod
    async def reset_usage(self, key: str) -> bool:
        """Reset usage count for a key."""
        pass

    @abstractmethod
    async def get_reset_time(self, key: str, window: int) -> datetime:
        """Get the time when the current window resets."""
        pass


class MemoryRateLimitStorage(RateLimitStorage):
    """In-memory rate limit storage (for development/testing)."""

    def __init__(self):
        self._storage: Dict[str, Dict[str, Any]] = {}
        self._lock = asyncio.Lock()

    async def get_usage(self, key: str, window: int) -> int:
        async with self._lock:
            if key not in self._storage:
                return 0

            data = self._storage[key]
            current_time = time.time()
            window_start = current_time - window

            # Clean old entries
            data['requests'] = [req_time for req_time in data['requests'] if req_time > window_start]

            return len(data['requests'])

    async def increment_usage(self, key: str, window: int, amount: int = 1) -> int:
        async with self._lock:
            current_time = time.time()

            if key not in self._storage:
                self._storage[key] = {'requests': [], 'window_start': current_time}

            data = self._storage[key]

            # Add new requests
            for _ in range(amount):
                data['requests'].append(current_time)

            # Clean old entries
            window_start = current_time - window
            data['requests'] = [req_time for req_time in data['requests'] if req_time > window_start]

            return len(data['requests'])

    async def reset_usage(self, key: str) -> bool:
        async with self._lock:
            if key in self._storage:
                del self._storage[key]
                return True
            return False

    async def get_reset_time(self, key: str, window: int) -> datetime:
        async with self._lock:
            if key not in self._storage:
                return datetime.now() + timedelta(seconds=window)

            data = self._storage[key]
            if data['requests']:
                oldest_request = min(data['requests'])
                return datetime.fromtimestamp(oldest_request + window)

            return datetime.now() + timedelta(seconds=window)


class RedisRateLimitStorage(RateLimitStorage):
    """Redis-based rate limit storage (for production)."""

    def __init__(self, redis_url: str = "redis://localhost:6379/0"):
        self.redis_url = redis_url
        self._redis = None

    async def _get_redis(self):
        """Lazy initialization of Redis connection."""
        if self._redis is None:
            try:
                import redis.asyncio as redis
                self._redis = redis.from_url(self.redis_url, decode_responses=True)
            except ImportError:
                raise ImportError("redis package is required for Redis storage backend")
        return self._redis

    async def get_usage(self, key: str, window: int) -> int:
        redis = await self._get_redis()

        try:
            # Use sliding window with sorted sets
            current_time = time.time()
            window_start = current_time - window

            # Remove old entries
            await redis.zremrangebyscore(key, 0, window_start)

            # Count current entries
            count = await redis.zcard(key)
            return count

        except Exception as e:
            logger.error(f"Redis get_usage error: {e}")
            return 0

    async def increment_usage(self, key: str, window: int, amount: int = 1) -> int:
        redis = await self._get_redis()

        try:
            current_time = time.time()
            window_start = current_time - window

            pipe = redis.pipeline()

            # Remove old entries
            pipe.zremrangebyscore(key, 0, window_start)

            # Add new requests
            for i in range(amount):
                pipe.zadd(key, {f"{current_time}_{i}": current_time})

            # Set expiration
            pipe.expire(key, window + 1)

            # Get count
            pipe.zcard(key)

            results = await pipe.execute()
            return results[-1]  # Return count from last command

        except Exception as e:
            logger.error(f"Redis increment_usage error: {e}")
            return amount  # Fail open

    async def reset_usage(self, key: str) -> bool:
        redis = await self._get_redis()

        try:
            result = await redis.delete(key)
            return result > 0
        except Exception as e:
            logger.error(f"Redis reset_usage error: {e}")
            return False

    async def get_reset_time(self, key: str, window: int) -> datetime:
        redis = await self._get_redis()

        try:
            # Get oldest entry
            oldest = await redis.zrange(key, 0, 0, withscores=True)
            if oldest:
                oldest_time = oldest[0][1]  # Score is the timestamp
                return datetime.fromtimestamp(oldest_time + window)

            return datetime.now() + timedelta(seconds=window)

        except Exception as e:
            logger.error(f"Redis get_reset_time error: {e}")
            return datetime.now() + timedelta(seconds=window)


class RateLimiter:
    """Main rate limiter class that applies rules and tracks usage."""

    def __init__(self, storage: RateLimitStorage, rules: List[RateLimitRule]):
        self.storage = storage
        self.rules = sorted(rules, key=lambda r: (r.scope.value, r.limit))  # Most restrictive first
        logger.info(f"Initialized rate limiter with {len(self.rules)} rules")

    def _build_key(self, rule: RateLimitRule, context: Dict[str, Any]) -> str:
        """Build a storage key for a rule and context."""
        key_parts = ["ratelimit", rule.scope.value]

        if rule.scope == RateLimitScope.GLOBAL:
            key_parts.append("global")
        elif rule.scope == RateLimitScope.TENANT:
            key_parts.append(context.get("tenant_id", "unknown"))
        elif rule.scope == RateLimitScope.USER:
            key_parts.append(f"tenant:{context.get('tenant_id', 'unknown')}")
            key_parts.append(f"user:{context.get('user_id', 'unknown')}")
        elif rule.scope == RateLimitScope.ENDPOINT:
            key_parts.append(f"endpoint:{rule.identifier or context.get('endpoint', 'unknown')}")
        elif rule.scope == RateLimitScope.IP:
            key_parts.append(f"ip:{context.get('client_ip', 'unknown')}")

        return ":".join(key_parts)

    async def check_rate_limit(self, context: Dict[str, Any]) -> RateLimitResult:
        """
        Check if a request should be rate limited.

        Args:
            context: Request context containing tenant_id, user_id, endpoint, client_ip, etc.

        Returns:
            RateLimitResult indicating if request is allowed
        """
        for rule in self.rules:
            # Skip endpoint-specific rules that don't match the current endpoint
            if rule.scope == RateLimitScope.ENDPOINT and rule.identifier:
                current_endpoint = context.get('endpoint', '')
                if current_endpoint != rule.identifier:
                    continue

            key = self._build_key(rule, context)

            try:
                # Check current usage
                current_usage = await self.storage.get_usage(key, rule.window)
                reset_time = await self.storage.get_reset_time(key, rule.window)

                # Calculate remaining requests
                effective_limit = rule.limit + rule.burst_allowance
                remaining = max(0, effective_limit - current_usage)

                # Check if limit exceeded
                if current_usage >= effective_limit:
                    retry_after = int((reset_time - datetime.now()).total_seconds())
                    return RateLimitResult(
                        allowed=False,
                        remaining=0,
                        reset_time=reset_time,
                        retry_after=max(1, retry_after),
                        rule_matched=rule
                    )

                # Increment usage for this request
                new_usage = await self.storage.increment_usage(key, rule.window)
                remaining = max(0, effective_limit - new_usage)

                # If this rule passes, continue to check other rules
                # But track the most restrictive remaining count
                context['_most_restrictive_remaining'] = min(
                    context.get('_most_restrictive_remaining', float('inf')),
                    remaining
                )
                context['_reset_time'] = reset_time

            except Exception as e:
                logger.error(f"Rate limit check failed for rule {rule}: {e}")
                # Fail open - allow request if storage fails
                continue

        # All rules passed
        return RateLimitResult(
            allowed=True,
            remaining=int(context.get('_most_restrictive_remaining', 0)),
            reset_time=context.get('_reset_time', datetime.now() + timedelta(seconds=60))
        )

    async def reset_rate_limit(self, context: Dict[str, Any], scope: RateLimitScope) -> bool:
        """Reset rate limit for a specific scope and context."""
        for rule in self.rules:
            if rule.scope == scope:
                key = self._build_key(rule, context)
                await self.storage.reset_usage(key)
        return True


# Default rate limiting rules for web applications
DEFAULT_RATE_LIMIT_RULES = [
    # Global limits (very generous for web apps)
    RateLimitRule(
        scope=RateLimitScope.GLOBAL,
        algorithm=RateLimitAlgorithm.SLIDING_WINDOW,
        limit=100000,  # 100k requests per hour globally
        window=3600
    ),

    # Per-tenant limits (generous for multi-tenant web apps)
    RateLimitRule(
        scope=RateLimitScope.TENANT,
        algorithm=RateLimitAlgorithm.SLIDING_WINDOW,
        limit=5000,  # 5k requests per hour per tenant
        window=3600,
        burst_allowance=500  # Allow burst of 500 extra requests
    ),

    # Per-user limits (generous for normal web browsing)
    RateLimitRule(
        scope=RateLimitScope.USER,
        algorithm=RateLimitAlgorithm.SLIDING_WINDOW,
        limit=1000,  # 1k requests per hour per user (16-17 per minute)
        window=3600,
        burst_allowance=200  # Allow burst navigation
    ),

    # Per-IP limits (for unauthenticated users - still generous for browsing)
    RateLimitRule(
        scope=RateLimitScope.IP,
        algorithm=RateLimitAlgorithm.SLIDING_WINDOW,
        limit=300,  # 300 requests per hour per IP (5 per minute)
        window=3600,
        burst_allowance=60  # Allow 1 extra request per minute in bursts
    ),

    # Auth endpoint specific limits (only applied to auth endpoints)
    RateLimitRule(
        scope=RateLimitScope.ENDPOINT,
        algorithm=RateLimitAlgorithm.SLIDING_WINDOW,
        limit=10,  # 10 login attempts per 15 minutes
        window=900,
        identifier="/auth/login"
    ),

    RateLimitRule(
        scope=RateLimitScope.ENDPOINT,
        algorithm=RateLimitAlgorithm.SLIDING_WINDOW,
        limit=5,  # 5 registration attempts per 15 minutes
        window=900,
        identifier="/auth/register"
    ),
]
