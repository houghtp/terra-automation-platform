"""
Task management API routes.
"""
from typing import Dict, Any
from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from app.features.core.task_manager import TaskManager, task_manager
from app.features.auth.dependencies import get_current_user
from app.features.auth.models import User
from app.deps.tenant import tenant_dependency
from app.features.core.sqlalchemy_imports import get_logger

logger = get_logger(__name__)
router = APIRouter()


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
    tenant_id: str = Depends(tenant_dependency),
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
        logger.error("Failed to start welcome email task", error=str(e), user_email=request.user_email)
        raise HTTPException(status_code=500, detail="Failed to start email task")


@router.post("/email/bulk", response_model=Dict[str, str])
async def send_bulk_email(
    request: BulkEmailRequest,
    tenant_id: str = Depends(tenant_dependency),
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
        logger.error("Failed to start bulk email task", error=str(e), recipient_count=len(request.recipient_emails))
        raise HTTPException(status_code=500, detail="Failed to start bulk email task")


@router.post("/data/export", response_model=Dict[str, str])
async def export_user_data(
    request: DataExportRequest,
    tenant_id: str = Depends(tenant_dependency),
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
        logger.error("Failed to start data export task", error=str(e), user_id=request.user_id)
        raise HTTPException(status_code=500, detail="Failed to start data export task")


@router.post("/reports/audit", response_model=Dict[str, str])
async def generate_audit_report(
    request: AuditReportRequest,
    tenant_id: str = Depends(tenant_dependency),
    current_user: User = Depends(get_current_user)
):
    """Generate audit report in background."""
    try:
        # SECURITY: Validate that user can only request audit for their own tenant
        if request.tenant_id != tenant_id:
            raise HTTPException(status_code=403, detail="Cannot generate audit report for different tenant")

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
        logger.error("Failed to start audit report task", error=str(e), tenant_id=request.tenant_id)
        raise HTTPException(status_code=500, detail="Failed to start audit report task")


@router.post("/cleanup/audit-logs", response_model=Dict[str, str])
async def cleanup_audit_logs(
    days_to_keep: int = 90,
    tenant_id: str = Depends(tenant_dependency),
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
        logger.error("Failed to start cleanup task", error=str(e), days_to_keep=days_to_keep)
        raise HTTPException(status_code=500, detail="Failed to start cleanup task")


@router.get("/status/{task_id}", response_model=Dict[str, Any])
async def get_task_status(
    task_id: str,
    tenant_id: str = Depends(tenant_dependency),
    current_user: User = Depends(get_current_user)
):
    """Get status of a background task."""
    try:
        status = TaskManager.get_task_status(task_id)
        return status
    except Exception as e:
        logger.error("Failed to get task status", error=str(e), task_id=task_id)
        raise HTTPException(status_code=500, detail="Failed to get task status")


@router.delete("/cancel/{task_id}", response_model=Dict[str, str])
async def cancel_task(
    task_id: str,
    tenant_id: str = Depends(tenant_dependency),
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
        logger.error("Failed to cancel task", error=str(e), task_id=task_id)
        raise HTTPException(status_code=500, detail="Failed to cancel task")


@router.get("/active", response_model=Dict[str, Any])
async def get_active_tasks(
    tenant_id: str = Depends(tenant_dependency),
    current_user: User = Depends(get_current_user)
):
    """Get information about active tasks."""
    try:
        active_tasks = TaskManager.get_active_tasks()
        return active_tasks
    except Exception as e:
        logger.error("Failed to get active tasks", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to get active tasks")


@router.get("/workers", response_model=Dict[str, Any])
async def get_worker_stats(
    tenant_id: str = Depends(tenant_dependency),
    current_user: User = Depends(get_current_user)
):
    """Get worker statistics."""
    try:
        worker_stats = TaskManager.get_worker_stats()
        return worker_stats
    except Exception as e:
        logger.error("Failed to get worker stats", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to get worker statistics")
