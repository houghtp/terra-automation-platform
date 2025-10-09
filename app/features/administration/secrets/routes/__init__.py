"""
Secrets routes module - provides organized route imports.
"""
from .crud_routes import router as crud_router
from .form_routes import router as form_router

__all__ = ["crud_router", "form_routes"]
