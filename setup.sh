#!/bin/bash

# TerraAutomationPlatform - Setup Script
# This script helps set up the development environment

echo "🚀 TerraAutomationPlatform Setup"
echo "========================================"

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed. Please install Python 3.8+ first."
    exit 1
fi

echo "✅ Python 3 found: $(python3 --version)"

# Check if pip is available
if ! command -v pip3 &> /dev/null; then
    echo "❌ pip3 is not installed. Please install pip first."
    exit 1
fi

echo "✅ pip3 found"

# Create virtual environment if it doesn't exist
if [ ! -d ".venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv .venv
    echo "✅ Virtual environment created"
else
    echo "✅ Virtual environment already exists"
fi

# Activate virtual environment
echo "🔄 Activating virtual environment..."
source .venv/bin/activate

# Install dependencies
echo "📥 Installing dependencies..."
pip install -r requirements.txt

echo "✅ Dependencies installed"

# Check if PostgreSQL is running
if command -v psql &> /dev/null; then
    echo "🔍 Checking PostgreSQL connection..."
    if psql -U postgres -d postgres -c '\q' 2>/dev/null; then
        echo "✅ PostgreSQL is running"

        # Create database if it doesn't exist
        echo "🗄️  Setting up database..."
        createdb -U postgres terra_automation_platform 2>/dev/null || echo "Database may already exist"

        # Run migrations
        echo "🔄 Running database migrations..."
        alembic upgrade head

        echo "✅ Database setup complete"
    else
        echo "⚠️  PostgreSQL is not accessible. Please ensure:"
        echo "   - PostgreSQL is installed and running"
        echo "   - User 'postgres' exists with appropriate permissions"
        echo "   - You can connect with: psql -U postgres"
    fi
else
    echo "⚠️  PostgreSQL client (psql) not found. Please install PostgreSQL."
fi

echo ""
echo "🎉 Setup complete!"
echo ""
echo "To start the application:"
echo "  1. Activate the virtual environment: source .venv/bin/activate"
echo "  2. Use VS Code debugger (F5) or run: uvicorn app.main:app --reload"
echo ""
echo "The application will be available at: http://localhost:8000"
echo "Admin dashboard: http://localhost:8000/administration"
echo "API Documentation: http://localhost:8000/docs"
echo ""
