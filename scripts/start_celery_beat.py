#!/usr/bin/env python3
"""
Start Celery beat scheduler for periodic tasks.
"""
import os
import sys
import subprocess
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def start_beat():
    """Start Celery beat scheduler."""
    print("⏰ Starting Celery beat scheduler...")

    # Set environment
    os.environ.setdefault("PYTHONPATH", str(project_root))

    # Celery beat command
    cmd = [
        "celery",
        "-A", "app.core.celery_app:celery_app",
        "beat",
        "--loglevel=info",
        "--schedule=/tmp/celerybeat-schedule"  # Temporary schedule file
    ]

    print(f"📋 Command: {' '.join(cmd)}")
    print("📅 Scheduled tasks:")
    print("   - cleanup-old-audit-logs: Daily")
    print("   - health-check: Every 5 minutes")
    print("🛑 Press Ctrl+C to stop")
    print("-" * 60)

    try:
        subprocess.run(cmd, cwd=project_root, check=True)
    except KeyboardInterrupt:
        print("\n🛑 Celery beat stopped")
    except subprocess.CalledProcessError as e:
        print(f"❌ Celery beat failed: {e}")
        return 1

    return 0

if __name__ == "__main__":
    exit(start_beat())