#!/usr/bin/env python
"""
Database management script.

This script provides a simple CLI for running database migrations with Alembic.

Usage:
    python manage_db.py migrate [--message MESSAGE]  # Create a new migration
    python manage_db.py upgrade [--revision REV]     # Upgrade to the specified revision (default: head)
    python manage_db.py downgrade [--revision REV]   # Downgrade to the specified revision
    python manage_db.py history                      # Show migration history
    python manage_db.py current                      # Show current revision
    python manage_db.py seed                         # Seed the database with sample data
"""
import argparse
import os
import subprocess
import sys
import asyncio


def run_alembic(args):
    """Run alembic with the given arguments."""
    # Try to run the alembic console script first. If it's not available on PATH
    # fall back to running the alembic module with the current Python executable.
    command = ["alembic"] + args
    print(f"Running: {' '.join(command)}")
    try:
        subprocess.run(command, check=True)
    except FileNotFoundError:
        # Fallback: run via python -m alembic
        py_cmd = [sys.executable, "-m", "alembic"] + args
        print(f"'alembic' not found on PATH, falling back to: {' '.join(py_cmd)}")
        subprocess.run(py_cmd, check=True)


def main():
    """Parse arguments and run the appropriate command."""
    parser = argparse.ArgumentParser(description="Database management script")
    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # Migrate command
    migrate_parser = subparsers.add_parser("migrate", help="Create a new migration")
    migrate_parser.add_argument("--message", "-m", help="Migration message")

    # Upgrade command
    upgrade_parser = subparsers.add_parser("upgrade", help="Upgrade to a later version")
    upgrade_parser.add_argument("--revision", "-r", default="head", help="Revision to upgrade to")

    # Downgrade command
    downgrade_parser = subparsers.add_parser("downgrade", help="Revert to a previous version")
    downgrade_parser.add_argument("--revision", "-r", required=True, help="Revision to downgrade to")

    # History command
    subparsers.add_parser("history", help="Show migration history")

    # Current command
    subparsers.add_parser("current", help="Show current revision")

    # Seed command
    subparsers.add_parser("seed", help="Seed the database with sample data")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    # Handle each command
    if args.command == "migrate":
        alembic_args = ["revision", "--autogenerate"]
        if args.message:
            alembic_args.extend(["-m", args.message])
        run_alembic(alembic_args)

    elif args.command == "upgrade":
        run_alembic(["upgrade", args.revision])

    elif args.command == "downgrade":
        run_alembic(["downgrade", args.revision])

    elif args.command == "history":
        run_alembic(["history"])

    elif args.command == "current":
        run_alembic(["current"])

    elif args.command == "seed":
        # Import seed_data lazily to avoid importing app modules during other commands
        from app.seed_data import seed_data
        print("Seeding database...")
        asyncio.run(seed_data())


if __name__ == "__main__":
    main()
