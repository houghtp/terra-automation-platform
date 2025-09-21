#!/bin/bash
# Setup development environment with PostgreSQL

set -e  # Exit on any error

echo "🚀 Setting up FastAPI Template Development Environment"
echo "======================================================"

# Check if Docker is running
if ! docker info >/dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker and try again."
    exit 1
fi

# Check if docker-compose exists and is working
export DOCKER_HOST=""  # Clear any problematic DOCKER_HOST setting
if ! docker-compose --version >/dev/null 2>&1; then
    echo "❌ docker-compose not working properly. Trying alternative setup..."
    # Try to start PostgreSQL directly with docker
    docker pull postgres:15
    docker run -d \
        --name fastapi_template_dev_db \
        -e POSTGRES_DB=fastapi_template_dev \
        -e POSTGRES_USER=dev_user \
        -e POSTGRES_PASSWORD=dev_password \
        -p 5432:5432 \
        postgres:15
    echo "✅ Started PostgreSQL container directly"
else
    echo "✅ docker-compose is available"
fi

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    echo "📝 Creating .env file from template..."
    cp .env.example .env
    echo "✅ Created .env file"
else
    echo "📝 .env file already exists"
fi

# Start PostgreSQL development database
echo "🐘 Starting PostgreSQL development database..."

# Try docker-compose first, then fallback to direct docker
if docker-compose --version >/dev/null 2>&1; then
    echo "Using docker-compose..."
    docker-compose up -d postgres-dev 2>/dev/null || {
        echo "⚠️  docker-compose failed, using direct docker..."
        # Remove any existing container
        docker stop fastapi_template_dev_db 2>/dev/null || true
        docker rm fastapi_template_dev_db 2>/dev/null || true

        # Start with direct docker
        docker run -d \
            --name fastapi_template_dev_db \
            -e POSTGRES_DB=fastapi_template_dev \
            -e POSTGRES_USER=dev_user \
            -e POSTGRES_PASSWORD=dev_password \
            -p 5434:5432 \
            postgres:15
    }
else
    echo "Using direct docker..."
    # Remove any existing container
    docker stop fastapi_template_dev_db 2>/dev/null || true
    docker rm fastapi_template_dev_db 2>/dev/null || true

    # Start with direct docker
    docker run -d \
        --name fastapi_template_dev_db \
        -e POSTGRES_DB=fastapi_template_dev \
        -e POSTGRES_USER=dev_user \
        -e POSTGRES_PASSWORD=dev_password \
        -p 5434:5432 \
        postgres:15
fi

# Wait for database to be ready
echo "⏳ Waiting for database to be ready..."
for i in {1..30}; do
    # Try to connect to PostgreSQL
    if docker exec fastapi_template_dev_db pg_isready -U dev_user -d fastapi_template_dev >/dev/null 2>&1; then
        echo "✅ Database is ready!"
        break
    fi

    if [ $i -eq 30 ]; then
        echo "❌ Database failed to start after 30 seconds"
        echo "Checking container status..."
        docker ps -a | grep fastapi_template_dev_db || echo "Container not found"
        docker logs fastapi_template_dev_db 2>/dev/null || echo "No logs available"
        exit 1
    fi

    sleep 2
done

# Run migrations
echo "🔄 Running database migrations..."
if command -v alembic >/dev/null 2>&1; then
    alembic upgrade head
    echo "✅ Migrations completed"
else
    echo "⚠️  Alembic not found. Please install requirements and run: alembic upgrade head"
fi

echo ""
echo "🎉 Development environment setup complete!"
echo ""
echo "🔗 Connection details:"
echo "   Database: fastapi_template_dev"
echo "   Host: localhost"
echo "   Port: 5432"
echo "   User: dev_user"
echo "   Password: dev_password"
echo ""
echo "🚀 To start the application:"
echo "   uvicorn app.main:app --reload"
echo ""
echo "🧪 To run tests:"
echo "   # Start test database:"
echo "   docker run -d --name fastapi_template_test_db -e POSTGRES_DB=fastapi_template_test -e POSTGRES_USER=test_user -e POSTGRES_PASSWORD=test_password -p 5433:5432 postgres:15"
echo "   # Run tests:"
echo "   pytest"
echo ""
echo "🛑 To stop databases:"
echo "   docker stop fastapi_template_dev_db fastapi_template_test_db"
echo "   docker rm fastapi_template_dev_db fastapi_template_test_db"
