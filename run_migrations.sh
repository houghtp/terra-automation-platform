#!/bin/bash
# Simple migration runner for Railway
set -e

echo "Running database migrations..."
alembic upgrade head
echo "Migrations complete!"
