#!/usr/bin/env python3
"""
Start Celery Flower monitoring dashboard.
"""
import os
import sys
import subprocess
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def start_flower():
    """Start Celery Flower monitoring."""
    print("🌸 Starting Celery Flower monitoring dashboard...")

    # Set environment
    os.environ.setdefault("PYTHONPATH", str(project_root))

    # Flower command
    cmd = [
        "celery",
        "-A", "app.core.celery_app:celery_app",
        "flower",
        "--port=5555",
        "--broker=redis://localhost:6379/0"
    ]

    print(f"📋 Command: {' '.join(cmd)}")
    print("🌐 Flower dashboard will be available at: http://localhost:5555")
    print("📊 Features: Task monitoring, worker stats, broker info")
    print("🛑 Press Ctrl+C to stop")
    print("-" * 60)

    try:
        subprocess.run(cmd, cwd=project_root, check=True)
    except KeyboardInterrupt:
        print("\n🛑 Celery Flower stopped")
    except subprocess.CalledProcessError as e:
        print(f"❌ Celery Flower failed: {e}")
        print("💡 Note: You may need to install flower: pip install flower")
        return 1

    return 0

if __name__ == "__main__":
    exit(start_flower())