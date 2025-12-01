#!/usr/bin/env python3
"""
One-time migration script for Railway.
Run this via Railway dashboard: Settings > Deploy > Run: python migrate.py
"""
import subprocess
import sys

def main():
    print("🔄 Running database migrations...")
    try:
        result = subprocess.run(
            ["alembic", "upgrade", "head"],
            check=True,
            capture_output=True,
            text=True
        )
        print(result.stdout)
        print("✅ Migrations completed successfully!")
        return 0
    except subprocess.CalledProcessError as e:
        print(f"❌ Migration failed: {e}")
        print(e.stdout)
        print(e.stderr)
        return 1

if __name__ == "__main__":
    sys.exit(main())
