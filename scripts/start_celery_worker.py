#!/usr/bin/env python3
"""
Start Celery worker for development.
"""
import os
import sys
import subprocess
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def start_worker():
    """Start Celery worker."""
    print("🚀 Starting Celery worker...")

    # Set environment
    os.environ.setdefault("PYTHONPATH", str(project_root))

    # Celery worker command
    cmd = [
        "celery",
        "-A", "app.core.celery_app:celery_app",
        "worker",
        "--loglevel=info",
        "--concurrency=2",  # 2 concurrent processes for development
        "--queues=default,email,data_processing,cleanup"
    ]

    print(f"📋 Command: {' '.join(cmd)}")
    print("📝 Available queues: default, email, data_processing, cleanup")
    print("🔄 Worker will auto-reload on code changes")
    print("🛑 Press Ctrl+C to stop")
    print("-" * 60)

    try:
        subprocess.run(cmd, cwd=project_root, check=True)
    except KeyboardInterrupt:
        print("\n🛑 Celery worker stopped")
    except subprocess.CalledProcessError as e:
        print(f"❌ Celery worker failed: {e}")
        return 1

    return 0

if __name__ == "__main__":
    exit(start_worker())