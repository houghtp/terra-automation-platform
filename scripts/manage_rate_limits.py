#!/usr/bin/env python3
"""
Rate limiting management CLI tool.
Provides utilities for managing, monitoring, and testing rate limits.
"""
import asyncio
import argparse
import sys
import json
from datetime import datetime, timedelta
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

try:
    from app.features.core.rate_limiting import (
        RateLimiter,
        MemoryRateLimitStorage,
        RedisRateLimitStorage,
        DEFAULT_RATE_LIMIT_RULES,
        RateLimitScope
    )
    from app.middleware.rate_limiting import create_strict_rate_limits, create_generous_rate_limits
except ImportError as e:
    logger.error(f"Failed to import rate limiting modules: {e}")
    logger.error("Make sure you're running this from the project root directory")
    sys.exit(1)


async def list_rules():
    """List all configured rate limiting rules."""
    logger.info("Default Rate Limiting Rules:")
    logger.info("=" * 50)

    for i, rule in enumerate(DEFAULT_RATE_LIMIT_RULES, 1):
        logger.info(f"{i}. {rule.scope.value.upper()} Rate Limit")
        logger.info(f"   Algorithm: {rule.algorithm.value}")
        logger.info(f"   Limit: {rule.limit} requests per {rule.window} seconds")
        if rule.burst_allowance:
            logger.info(f"   Burst Allowance: +{rule.burst_allowance} requests")
        if rule.identifier:
            logger.info(f"   Identifier: {rule.identifier}")
        logger.info("")


async def test_rate_limits():
    """Test rate limiting functionality."""
    logger.info("Testing rate limiting functionality...")

    # Create test storage and rate limiter
    storage = MemoryRateLimitStorage()
    rate_limiter = RateLimiter(storage=storage, rules=DEFAULT_RATE_LIMIT_RULES)

    # Test context
    test_context = {
        "tenant_id": "test-tenant",
        "user_id": "test-user",
        "client_ip": "127.0.0.1",
        "endpoint": "/api/test",
        "authenticated": True
    }

    logger.info("Sending test requests...")

    allowed_count = 0
    denied_count = 0

    # Send multiple requests to test limits
    for i in range(15):
        result = await rate_limiter.check_rate_limit(test_context)

        if result.allowed:
            allowed_count += 1
            logger.info(f"Request {i+1}: ✅ Allowed (remaining: {result.remaining})")
        else:
            denied_count += 1
            logger.info(f"Request {i+1}: ❌ Denied (retry after: {result.retry_after}s)")

        # Small delay between requests
        await asyncio.sleep(0.1)

    logger.info(f"\nTest Results:")
    logger.info(f"  Allowed: {allowed_count}")
    logger.info(f"  Denied: {denied_count}")
    logger.info(f"  Rate limiting is {'working correctly' if denied_count > 0 else 'not triggered'}")


async def check_storage():
    """Check rate limiting storage backend connectivity."""
    import os

    logger.info("Checking storage backend connectivity...")

    environment = os.getenv("ENVIRONMENT", "development")
    redis_url = os.getenv("REDIS_URL", os.getenv("RATE_LIMIT_REDIS_URL"))

    logger.info(f"Environment: {environment}")
    logger.info(f"Redis URL: {redis_url or 'not configured'}")

    # Test memory storage
    logger.info("\n1. Testing Memory Storage:")
    try:
        memory_storage = MemoryRateLimitStorage()
        test_key = "test:memory"

        # Test basic operations
        usage = await memory_storage.get_usage(test_key, 60)
        logger.info(f"   ✅ get_usage: {usage}")

        new_usage = await memory_storage.increment_usage(test_key, 60, 5)
        logger.info(f"   ✅ increment_usage: {new_usage}")

        reset_result = await memory_storage.reset_usage(test_key)
        logger.info(f"   ✅ reset_usage: {reset_result}")

        reset_time = await memory_storage.get_reset_time(test_key, 60)
        logger.info(f"   ✅ get_reset_time: {reset_time}")

        logger.info("   Memory storage is working correctly!")

    except Exception as e:
        logger.error(f"   ❌ Memory storage test failed: {e}")

    # Test Redis storage if configured
    if redis_url:
        logger.info("\n2. Testing Redis Storage:")
        try:
            redis_storage = RedisRateLimitStorage(redis_url)
            test_key = "test:redis"

            # Test basic operations
            usage = await redis_storage.get_usage(test_key, 60)
            logger.info(f"   ✅ get_usage: {usage}")

            new_usage = await redis_storage.increment_usage(test_key, 60, 3)
            logger.info(f"   ✅ increment_usage: {new_usage}")

            reset_result = await redis_storage.reset_usage(test_key)
            logger.info(f"   ✅ reset_usage: {reset_result}")

            reset_time = await redis_storage.get_reset_time(test_key, 60)
            logger.info(f"   ✅ get_reset_time: {reset_time}")

            logger.info("   Redis storage is working correctly!")

        except ImportError:
            logger.warning("   ⚠️  Redis package not installed (pip install redis)")
        except Exception as e:
            logger.error(f"   ❌ Redis storage test failed: {e}")
    else:
        logger.info("\n2. Redis Storage: Not configured")


async def monitor_usage(duration: int = 60):
    """Monitor rate limiting usage in real-time."""
    import os

    logger.info(f"Monitoring rate limiting usage for {duration} seconds...")
    logger.info("Press Ctrl+C to stop early")

    # Try to connect to Redis for monitoring
    redis_url = os.getenv("REDIS_URL", os.getenv("RATE_LIMIT_REDIS_URL"))

    if not redis_url:
        logger.warning("Redis not configured, cannot monitor real usage")
        return

    try:
        storage = RedisRateLimitStorage(redis_url)

        start_time = datetime.now()
        end_time = start_time + timedelta(seconds=duration)

        while datetime.now() < end_time:
            logger.info("\n--- Rate Limiting Usage ---")

            # Monitor different scopes
            scopes_to_monitor = [
                ("global", "ratelimit:global:global"),
                ("tenant example", "ratelimit:tenant:example-tenant"),
                ("user example", "ratelimit:user:tenant:example-tenant:user:example-user"),
                ("ip example", "ratelimit:ip:ip:127.0.0.1"),
            ]

            for scope_name, key_pattern in scopes_to_monitor:
                try:
                    usage = await storage.get_usage(key_pattern, 3600)  # 1 hour window
                    reset_time = await storage.get_reset_time(key_pattern, 3600)
                    logger.info(f"{scope_name}: {usage} requests (resets at {reset_time.strftime('%H:%M:%S')})")
                except Exception as e:
                    logger.debug(f"Error monitoring {scope_name}: {e}")

            await asyncio.sleep(5)  # Update every 5 seconds

    except ImportError:
        logger.error("Redis package not installed")
    except KeyboardInterrupt:
        logger.info("\nMonitoring stopped by user")
    except Exception as e:
        logger.error(f"Monitoring failed: {e}")


async def reset_limits(scope: str, identifier: str = None):
    """Reset rate limits for a specific scope."""
    import os

    logger.info(f"Resetting rate limits for scope: {scope}")

    redis_url = os.getenv("REDIS_URL", os.getenv("RATE_LIMIT_REDIS_URL"))

    if redis_url:
        try:
            storage = RedisRateLimitStorage(redis_url)

            # Build key pattern based on scope
            if scope == "global":
                key = "ratelimit:global:global"
            elif scope == "tenant" and identifier:
                key = f"ratelimit:tenant:{identifier}"
            elif scope == "user" and identifier:
                key = f"ratelimit:user:tenant:*:user:{identifier}"
            elif scope == "ip" and identifier:
                key = f"ratelimit:ip:ip:{identifier}"
            else:
                logger.error("Invalid scope or missing identifier")
                return

            success = await storage.reset_usage(key)
            if success:
                logger.info(f"✅ Reset successful for {key}")
            else:
                logger.warning(f"⚠️  Reset may have failed for {key}")

        except Exception as e:
            logger.error(f"Reset failed: {e}")
    else:
        logger.warning("Redis not configured, cannot reset limits")


async def generate_config():
    """Generate rate limiting configuration examples."""
    logger.info("Rate Limiting Configuration Examples:")
    logger.info("=" * 50)

    configs = {
        "default": DEFAULT_RATE_LIMIT_RULES,
        "strict": create_strict_rate_limits(),
        "generous": create_generous_rate_limits()
    }

    for config_name, rules in configs.items():
        logger.info(f"\n{config_name.upper()} Configuration:")
        logger.info("-" * 30)

        config_dict = {
            "rules": [rule.to_dict() for rule in rules]
        }

        logger.info(json.dumps(config_dict, indent=2, default=str))


def main():
    parser = argparse.ArgumentParser(description="Rate limiting management CLI")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # List command
    list_parser = subparsers.add_parser("list", help="List all rate limiting rules")

    # Test command
    test_parser = subparsers.add_parser("test", help="Test rate limiting functionality")

    # Check command
    check_parser = subparsers.add_parser("check", help="Check storage backend connectivity")

    # Monitor command
    monitor_parser = subparsers.add_parser("monitor", help="Monitor rate limiting usage")
    monitor_parser.add_argument("--duration", type=int, default=60, help="Duration in seconds (default: 60)")

    # Reset command
    reset_parser = subparsers.add_parser("reset", help="Reset rate limits for a scope")
    reset_parser.add_argument("scope", choices=["global", "tenant", "user", "ip"], help="Scope to reset")
    reset_parser.add_argument("--identifier", help="Identifier for the scope (required for tenant/user/ip)")

    # Config command
    config_parser = subparsers.add_parser("config", help="Generate configuration examples")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    try:
        if args.command == "list":
            asyncio.run(list_rules())
        elif args.command == "test":
            asyncio.run(test_rate_limits())
        elif args.command == "check":
            asyncio.run(check_storage())
        elif args.command == "monitor":
            asyncio.run(monitor_usage(args.duration))
        elif args.command == "reset":
            asyncio.run(reset_limits(args.scope, args.identifier))
        elif args.command == "config":
            asyncio.run(generate_config())
    except KeyboardInterrupt:
        logger.info("Operation cancelled")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Command failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
