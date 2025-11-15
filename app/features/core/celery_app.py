"""
Celery application configuration for background tasks.
"""
import os
from celery import Celery
from kombu import Queue

# Read configuration from environment
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", REDIS_URL)
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", REDIS_URL)

# Create Celery app
celery_app = Celery(
    "fastapi_template",
    broker=CELERY_BROKER_URL,
    backend=CELERY_RESULT_BACKEND,
    include=[
        "app.features.tasks.email_tasks",
        "app.features.tasks.data_processing_tasks",
        "app.features.tasks.cleanup_tasks",
        "app.features.msp.cspm.tasks",  # CSPM compliance scan tasks
        "app.features.business_automations.content_broadcaster.tasks",
    ]
)

# Celery configuration
celery_app.conf.update(
    # Task routing
    task_routes={
        "app.features.tasks.email_tasks.*": {"queue": "email"},
        "app.features.tasks.data_processing_tasks.*": {"queue": "data_processing"},
        "app.features.tasks.cleanup_tasks.*": {"queue": "cleanup"},
        "app.features.business_automations.content_broadcaster.tasks.*": {"queue": "content_broadcaster"},
    },

    # Queue definitions
    task_default_queue="default",
    task_queues=(
        Queue("default"),
        Queue("email"),
        Queue("data_processing"),
        Queue("cleanup"),
        Queue("content_broadcaster"),
    ),

    # Task execution settings
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,

    # Task result settings
    result_expires=3600,  # 1 hour
    result_persistent=True,

    # Worker settings
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    worker_disable_rate_limits=False,

    # Retry settings
    task_reject_on_worker_lost=True,
    task_default_retry_delay=60,  # 1 minute
    task_max_retries=3,

    # Monitoring
    worker_send_task_events=True,
    task_send_sent_event=True,

    # Beat schedule (for periodic tasks)
    beat_schedule={
        "cleanup-old-audit-logs": {
            "task": "app.features.tasks.cleanup_tasks.cleanup_old_audit_logs",
            "schedule": 86400.0,  # Run daily (86400 seconds)
        },
        "health-check": {
            "task": "app.features.tasks.cleanup_tasks.health_check_task",
            "schedule": 300.0,  # Run every 5 minutes
        },
    },
)

# Auto-discover tasks in modules
celery_app.autodiscover_tasks()

if __name__ == "__main__":
    celery_app.start()
