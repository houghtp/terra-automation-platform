"""
Task management API routes.
"""
import logging
from typing import Dict, Any
from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from app.features.core.task_manager import TaskManager, task_manager
from app.features.auth.dependencies import get_current_user
from app.features.auth.models import User

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/administration/tasks")


# Request models
class EmailTaskRequest(BaseModel):
    user_email: str
    user_name: str


class BulkEmailRequest(BaseModel):
    recipient_emails: list[str]
    subject: str
    message: str


class DataExportRequest(BaseModel):
    user_id: int
    export_format: str = "csv"


class AuditReportRequest(BaseModel):
    tenant_id: str
    start_date: str
    end_date: str


@router.post("/email/welcome", response_model=Dict[str, str])
async def send_welcome_email(
    request: EmailTaskRequest,
    current_user: User = Depends(get_current_user)
):
    """Send welcome email in background."""
    try:
        task_id = TaskManager.start_task(
            "app.features.tasks.email_tasks.send_welcome_email",
            request.user_email,
            request.user_name
        )

        return {
            "status": "started",
            "task_id": task_id,
            "message": f"Welcome email task started for {request.user_email}"
        }
    except Exception as e:
        logger.error(f"Failed to start welcome email task: {e}")
        raise HTTPException(status_code=500, detail="Failed to start email task")


@router.post("/email/bulk", response_model=Dict[str, str])
async def send_bulk_email(
    request: BulkEmailRequest,
    current_user: User = Depends(get_current_user)
):
    """Send bulk email in background."""
    try:
        task_id = TaskManager.start_task(
            "app.features.tasks.email_tasks.send_bulk_notification",
            request.recipient_emails,
            request.subject,
            request.message
        )

        return {
            "status": "started",
            "task_id": task_id,
            "message": f"Bulk email task started for {len(request.recipient_emails)} recipients"
        }
    except Exception as e:
        logger.error(f"Failed to start bulk email task: {e}")
        raise HTTPException(status_code=500, detail="Failed to start bulk email task")


@router.post("/data/export", response_model=Dict[str, str])
async def export_user_data(
    request: DataExportRequest,
    current_user: User = Depends(get_current_user)
):
    """Start user data export in background."""
    try:
        task_id = TaskManager.start_task(
            "app.features.tasks.data_processing_tasks.process_user_data_export",
            request.user_id,
            request.export_format
        )

        return {
            "status": "started",
            "task_id": task_id,
            "message": f"Data export task started for user {request.user_id}"
        }
    except Exception as e:
        logger.error(f"Failed to start data export task: {e}")
        raise HTTPException(status_code=500, detail="Failed to start data export task")


@router.post("/reports/audit", response_model=Dict[str, str])
async def generate_audit_report(
    request: AuditReportRequest,
    current_user: User = Depends(get_current_user)
):
    """Generate audit report in background."""
    try:
        task_id = TaskManager.start_task(
            "app.features.tasks.data_processing_tasks.generate_audit_report",
            request.tenant_id,
            request.start_date,
            request.end_date
        )

        return {
            "status": "started",
            "task_id": task_id,
            "message": f"Audit report generation started for tenant {request.tenant_id}"
        }
    except Exception as e:
        logger.error(f"Failed to start audit report task: {e}")
        raise HTTPException(status_code=500, detail="Failed to start audit report task")


@router.post("/cleanup/audit-logs", response_model=Dict[str, str])
async def cleanup_audit_logs(
    days_to_keep: int = 90,
    current_user: User = Depends(get_current_user)
):
    """Start audit log cleanup in background."""
    try:
        task_id = TaskManager.start_task(
            "app.features.tasks.cleanup_tasks.cleanup_old_audit_logs",
            days_to_keep
        )

        return {
            "status": "started",
            "task_id": task_id,
            "message": f"Audit log cleanup started (keeping {days_to_keep} days)"
        }
    except Exception as e:
        logger.error(f"Failed to start cleanup task: {e}")
        raise HTTPException(status_code=500, detail="Failed to start cleanup task")


@router.get("/status/{task_id}", response_model=Dict[str, Any])
async def get_task_status(
    task_id: str,
    current_user: User = Depends(get_current_user)
):
    """Get status of a background task."""
    try:
        status = TaskManager.get_task_status(task_id)
        return status
    except Exception as e:
        logger.error(f"Failed to get task status: {e}")
        raise HTTPException(status_code=500, detail="Failed to get task status")


@router.delete("/cancel/{task_id}", response_model=Dict[str, str])
async def cancel_task(
    task_id: str,
    current_user: User = Depends(get_current_user)
):
    """Cancel a background task."""
    try:
        success = TaskManager.cancel_task(task_id)
        if success:
            return {
                "status": "cancelled",
                "task_id": task_id,
                "message": "Task cancelled successfully"
            }
        else:
            raise HTTPException(status_code=400, detail="Failed to cancel task")
    except Exception as e:
        logger.error(f"Failed to cancel task: {e}")
        raise HTTPException(status_code=500, detail="Failed to cancel task")


@router.get("/active", response_model=Dict[str, Any])
async def get_active_tasks(current_user: User = Depends(get_current_user)):
    """Get information about active tasks."""
    try:
        active_tasks = TaskManager.get_active_tasks()
        return active_tasks
    except Exception as e:
        logger.error(f"Failed to get active tasks: {e}")
        raise HTTPException(status_code=500, detail="Failed to get active tasks")


@router.get("/workers", response_model=Dict[str, Any])
async def get_worker_stats(current_user: User = Depends(get_current_user)):
    """Get worker statistics."""
    try:
        worker_stats = TaskManager.get_worker_stats()
        return worker_stats
    except Exception as e:
        logger.error(f"Failed to get worker stats: {e}")
        raise HTTPException(status_code=500, detail="Failed to get worker statistics")