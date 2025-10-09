"""
Centralized route imports and utilities for FastAPI routes.
Use this module to standardize route patterns across all slices.
"""

# Core FastAPI imports
from fastapi import APIRouter, Depends, Request, HTTPException, Body, Form, Response, Query
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

# Core application imports
from app.features.core.templates import templates
from app.features.core.database import get_db
from app.features.core.validation import FormHandler
from app.features.core.rate_limiter import rate_limit_api
from app.deps.tenant import tenant_dependency
from app.features.auth.dependencies import get_current_user, get_global_admin_user
from app.features.auth.models import User

# Python standard library
from typing import Optional, List, Dict, Any
import structlog

# Export commonly used combinations
__all__ = [
    # FastAPI core
    'APIRouter', 'Depends', 'Request', 'HTTPException', 'Body', 'Form', 'Response', 'Query',

    # Response types
    'HTMLResponse', 'JSONResponse', 'RedirectResponse',

    # Database
    'AsyncSession', 'get_db',

    # Templates and validation
    'templates', 'FormHandler',

    # Rate limiting
    'rate_limit_api',

    # Dependencies
    'tenant_dependency', 'get_current_user', 'get_global_admin_user', 'User',

    # Typing
    'Optional', 'List', 'Dict', 'Any',

    # Logging
    'structlog', 'get_logger',

    # Utilities
    'handle_route_error', 'commit_transaction', 'create_success_response',
    'create_error_response', 'is_global_admin'
]


def get_logger(name: str):
    """Standardized logger creation for routes."""
    return structlog.get_logger(name)


def handle_route_error(operation: str, error: Exception, **context):
    """Standardized route error handling with logging."""
    logger = get_logger("route_handler")
    logger.error("Route operation failed",
                operation=operation,
                error=str(error),
                **context)


async def commit_transaction(db: AsyncSession, operation: str):
    """Standardized transaction commit with error handling."""
    try:
        await db.commit()
    except Exception as e:
        await db.rollback()
        handle_route_error(operation, e)
        raise HTTPException(status_code=500, detail=f"Failed to {operation}")


def create_success_response(message: str = None):
    """Create standardized success response for HTMX."""
    if message:
        return JSONResponse({"success": True, "message": message})
    return Response(status_code=204)


def create_error_response(message: str, status_code: int = 400):
    """Create standardized error response."""
    return JSONResponse(
        status_code=status_code,
        content={"error": message, "success": False}
    )


def is_global_admin(user: User) -> bool:
    """Check if user is global admin."""
    return user.role == "global_admin" and user.tenant_id == "global"
