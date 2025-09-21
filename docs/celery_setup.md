# Celery Background Tasks Setup

This document explains how to set up and use Celery for background task processing in the FastAPI Template.

## Overview

The application uses **Celery** with **Redis** as the message broker for:
- ✉️ **Email sending** (welcome emails, password resets, notifications)
- 📊 **Data processing** (exports, reports, analytics)
- 🧹 **Cleanup tasks** (log cleanup, session cleanup, maintenance)
- ⏰ **Scheduled tasks** (periodic maintenance, health checks)

## Quick Start

### 1. Start Redis (Message Broker)

```bash
# Using Docker (recommended)
docker-compose up -d redis-dev

# Or start Redis directly
redis-server
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Start Celery Worker

```bash
# Using the provided script
python scripts/start_celery_worker.py

# Or directly with celery command
celery -A app.core.celery_app:celery_app worker --loglevel=info --concurrency=2
```

### 4. Start Celery Beat (Optional - for scheduled tasks)

```bash
# Using the provided script
python scripts/start_celery_beat.py

# Or directly with celery command
celery -A app.core.celery_app:celery_app beat --loglevel=info
```

### 5. Start Flower Monitoring (Optional)

```bash
# Install flower first
pip install flower

# Start monitoring dashboard
python scripts/start_celery_flower.py

# Access dashboard at: http://localhost:5555
```

## Task Categories

### Email Tasks (`app.features.tasks.email_tasks`)
- `send_welcome_email`: Send welcome email to new users
- `send_password_reset_email`: Send password reset emails
- `send_bulk_notification`: Send bulk notifications
- `send_admin_alert`: Send alerts to administrators

### Data Processing Tasks (`app.features.tasks.data_processing_tasks`)
- `process_user_data_export`: Export user data in various formats
- `generate_audit_report`: Generate comprehensive audit reports
- `process_bulk_user_import`: Process bulk user imports from CSV/Excel
- `calculate_usage_analytics`: Calculate usage metrics and analytics

### Cleanup Tasks (`app.features.tasks.cleanup_tasks`)
- `cleanup_old_audit_logs`: Remove old audit log entries
- `cleanup_expired_sessions`: Clean up expired user sessions
- `cleanup_temporary_files`: Remove temporary files and uploads
- `optimize_database_tables`: Optimize database performance
- `health_check_task`: Periodic system health checks

## API Endpoints

All task endpoints are under `/administration/tasks/` and require authentication:

### Email Tasks
- `POST /administration/tasks/email/welcome` - Send welcome email
- `POST /administration/tasks/email/bulk` - Send bulk emails

### Data Tasks
- `POST /administration/tasks/data/export` - Export user data
- `POST /administration/tasks/reports/audit` - Generate audit report

### Cleanup Tasks
- `POST /administration/tasks/cleanup/audit-logs` - Clean up old audit logs

### Task Management
- `GET /administration/tasks/status/{task_id}` - Get task status
- `DELETE /administration/tasks/cancel/{task_id}` - Cancel task
- `GET /administration/tasks/active` - Get active tasks
- `GET /administration/tasks/workers` - Get worker statistics

## Usage Examples

### 1. Send Welcome Email

```python
from app.core.task_manager import send_welcome_email_async

# Start background task
task_id = send_welcome_email_async("user@example.com", "John Doe")

# Check status
from app.core.task_manager import TaskManager
status = TaskManager.get_task_status(task_id)
```

### 2. Generate Audit Report

```bash
curl -X POST "http://localhost:8000/administration/tasks/reports/audit" \\
  -H "Authorization: Bearer YOUR_TOKEN" \\
  -H "Content-Type: application/json" \\
  -d '{
    "tenant_id": "tenant_123",
    "start_date": "2024-01-01",
    "end_date": "2024-01-31"
  }'
```

### 3. Check Task Status

```bash
curl "http://localhost:8000/administration/tasks/status/TASK_ID" \\
  -H "Authorization: Bearer YOUR_TOKEN"
```

## Queue Configuration

Tasks are organized into queues for better resource management:

- **default**: General tasks
- **email**: Email sending tasks
- **data_processing**: Heavy data processing tasks
- **cleanup**: Maintenance and cleanup tasks

## Scheduled Tasks

The following tasks run automatically when Celery Beat is enabled:

- **Daily**: `cleanup_old_audit_logs` - Clean up audit logs older than 90 days
- **Every 5 minutes**: `health_check_task` - System health monitoring

## Development vs Production

### Development Setup
- Single worker process
- Redis on localhost
- File-based beat schedule
- Flower monitoring for debugging

### Production Considerations
- Multiple worker processes
- Redis cluster for high availability
- Database-backed beat schedule
- Proper logging and monitoring
- Error handling and retries
- Resource limits and scaling

## Configuration

Environment variables (in `.env`):

```env
# Redis Configuration
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0
```

## Docker Setup

For containerized deployment, add to `docker-compose.yml`:

```yaml
services:
  celery-worker:
    build: .
    command: celery -A app.core.celery_app:celery_app worker --loglevel=info
    depends_on:
      - redis-dev
      - postgres-dev
    environment:
      - DATABASE_URL=postgresql+asyncpg://dev_user:dev_password@postgres-dev:5432/fastapi_template_dev
      - REDIS_URL=redis://redis-dev:6379/0
    volumes:
      - .:/app

  celery-beat:
    build: .
    command: celery -A app.core.celery_app:celery_app beat --loglevel=info
    depends_on:
      - redis-dev
    environment:
      - REDIS_URL=redis://redis-dev:6379/0
    volumes:
      - .:/app
```

## Monitoring and Debugging

### Flower Dashboard
- **URL**: http://localhost:5555
- **Features**: Task monitoring, worker stats, broker info, task history

### Logs
- Worker logs show task execution
- Use structured logging for better debugging
- Check Redis logs for broker issues

### Common Issues
1. **Worker not starting**: Check Redis connection
2. **Tasks not executing**: Verify worker is running and connected
3. **Import errors**: Ensure all dependencies are installed
4. **Memory issues**: Adjust worker concurrency

## Best Practices

1. **Task Design**:
   - Keep tasks idempotent
   - Handle failures gracefully
   - Use proper retry logic
   - Add logging and monitoring

2. **Performance**:
   - Use appropriate queue routing
   - Monitor task execution times
   - Optimize heavy operations
   - Consider task chunking for large datasets

3. **Security**:
   - Validate task inputs
   - Use secure Redis configuration
   - Implement proper authentication
   - Audit task execution

4. **Testing**:
   - Test tasks in isolation
   - Mock external dependencies
   - Verify retry behavior
   - Test error handling

## Extending the System

To add new tasks:

1. Create task functions in appropriate modules
2. Add to `celery_app.py` includes
3. Create API endpoints if needed
4. Add convenience functions to `task_manager.py`
5. Update documentation

Example new task:

```python
from app.core.celery_app import celery_app

@celery_app.task(bind=True)
def my_new_task(self, param1: str, param2: int):
    try:
        # Task logic here
        return {"status": "success", "result": "data"}
    except Exception as exc:
        raise self.retry(exc=exc, countdown=60, max_retries=3)
```