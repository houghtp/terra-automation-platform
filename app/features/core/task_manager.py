"""
Task manager utilities for background task execution.
"""
import logging
from typing import Dict, Any, Optional
from celery.result import AsyncResult
from app.features.core.celery_app import celery_app

logger = logging.getLogger(__name__)


class TaskManager:
    """Utility class for managing background tasks."""

    @staticmethod
    def start_task(task_name: str, *args, **kwargs) -> str:
        """
        Start a background task.

        Args:
            task_name: Name of the task function
            *args: Positional arguments for the task
            **kwargs: Keyword arguments for the task

        Returns:
            Task ID
        """
        try:
            task = celery_app.send_task(task_name, args=args, kwargs=kwargs)
            logger.info(f"Started task {task_name} with ID: {task.id}")
            return task.id
        except Exception as exc:
            logger.error(f"Failed to start task {task_name}: {exc}")
            raise

    @staticmethod
    def get_task_status(task_id: str) -> Dict[str, Any]:
        """
        Get the status of a background task.

        Args:
            task_id: Task ID

        Returns:
            Dict with task status information
        """
        try:
            result = AsyncResult(task_id, app=celery_app)

            status_info = {
                "task_id": task_id,
                "status": result.status,
                "ready": result.ready(),
                "successful": result.successful() if result.ready() else None,
                "failed": result.failed() if result.ready() else None,
            }

            # Add result if task is complete
            if result.ready():
                if result.successful():
                    status_info["result"] = result.result
                elif result.failed():
                    status_info["error"] = str(result.result)
                    status_info["traceback"] = result.traceback

            # Add progress info if available
            if hasattr(result, 'info') and result.info:
                status_info["info"] = result.info

            return status_info

        except Exception as exc:
            logger.error(f"Failed to get task status for {task_id}: {exc}")
            return {
                "task_id": task_id,
                "status": "ERROR",
                "error": f"Failed to retrieve task status: {exc}"
            }

    @staticmethod
    def cancel_task(task_id: str) -> bool:
        """
        Cancel a background task.

        Args:
            task_id: Task ID

        Returns:
            True if cancelled successfully
        """
        try:
            celery_app.control.revoke(task_id, terminate=True)
            logger.info(f"Cancelled task: {task_id}")
            return True
        except Exception as exc:
            logger.error(f"Failed to cancel task {task_id}: {exc}")
            return False

    @staticmethod
    def get_active_tasks() -> Dict[str, Any]:
        """
        Get information about currently active tasks.

        Returns:
            Dict with active task information
        """
        try:
            inspect = celery_app.control.inspect()
            active_tasks = inspect.active()
            scheduled_tasks = inspect.scheduled()
            reserved_tasks = inspect.reserved()

            return {
                "active": active_tasks or {},
                "scheduled": scheduled_tasks or {},
                "reserved": reserved_tasks or {},
                "total_active": sum(len(tasks) for tasks in (active_tasks or {}).values()),
                "total_scheduled": sum(len(tasks) for tasks in (scheduled_tasks or {}).values()),
                "total_reserved": sum(len(tasks) for tasks in (reserved_tasks or {}).values()),
            }

        except Exception as exc:
            logger.error(f"Failed to get active tasks: {exc}")
            return {"error": f"Failed to retrieve active tasks: {exc}"}

    @staticmethod
    def get_worker_stats() -> Dict[str, Any]:
        """
        Get worker statistics.

        Returns:
            Dict with worker statistics
        """
        try:
            inspect = celery_app.control.inspect()
            stats = inspect.stats()
            ping = inspect.ping()

            return {
                "workers": list(ping.keys()) if ping else [],
                "worker_count": len(ping) if ping else 0,
                "stats": stats or {},
                "ping": ping or {}
            }

        except Exception as exc:
            logger.error(f"Failed to get worker stats: {exc}")
            return {"error": f"Failed to retrieve worker stats: {exc}"}


# Convenience functions for common tasks
def send_welcome_email_async(user_email: str, user_name: str, tenant_id: str = "default") -> str:
    """Send welcome email asynchronously."""
    return TaskManager.start_task("app.features.tasks.email_tasks.send_welcome_email", user_email, user_name, tenant_id)


def send_password_reset_email_async(user_email: str, reset_token: str, user_name: str = None, tenant_id: str = "default") -> str:
    """Send password reset email asynchronously."""
    return TaskManager.start_task("app.features.tasks.email_tasks.send_password_reset_email", user_email, reset_token, user_name, tenant_id)


def process_user_data_export_async(user_id: int, export_format: str = "csv") -> str:
    """Process user data export asynchronously."""
    return TaskManager.start_task("app.features.tasks.data_processing_tasks.process_user_data_export", user_id, export_format)


def generate_audit_report_async(tenant_id: str, start_date: str, end_date: str) -> str:
    """Generate audit report asynchronously."""
    return TaskManager.start_task("app.features.tasks.data_processing_tasks.generate_audit_report", tenant_id, start_date, end_date)


def cleanup_old_audit_logs_async(days_to_keep: int = 90) -> str:
    """Clean up old audit logs asynchronously."""
    return TaskManager.start_task("app.features.tasks.cleanup_tasks.cleanup_old_audit_logs", days_to_keep)


# Global task manager instance
task_manager = TaskManager()
