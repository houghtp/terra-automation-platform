#!/usr/bin/env python3
"""
Quick script to temporarily disable rate limiting for development.
"""

import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

print("=" * 60)
print("Rate Limiting - Development Mode")
print("=" * 60)

# Check current status
current_status = os.getenv("RATE_LIMITING_ENABLED", "true")
print(f"\nCurrent Status: {'ENABLED' if current_status.lower() in ('true', '1', 'yes') else 'DISABLED'}")

print("\n📝 To disable rate limiting for development:")
print("   1. Add to your .env file:")
print("      RATE_LIMITING_ENABLED=false")
print()
print("   2. Or export in your terminal:")
print("      export RATE_LIMITING_ENABLED=false")
print()
print("   3. Then restart your server")
print()

print("⏱️  Rate limit will reset in 15 minutes from last request")
print("   Current limit: 3 login attempts per 15 minutes")
print()

print("💡 To increase limits for development, you can:")
print("   - Wait 15 minutes")
print("   - Restart the server (clears memory cache)")
print("   - Use incognito/private browsing")
print("   - Clear your cookies")
print()
print("=" * 60)
