"""
Base audit mixin for consistent audit fields across all models.
Follows audit best practices with human-readable tracking.
"""

from sqlalchemy import Column, String, DateTime
from sqlalchemy.sql import func
from typing import Dict, Any, Optional


class AuditMixin:
    """
    Mixin class that provides standardized audit fields for all models.

    Stores human-readable audit information (email/username) rather than just IDs
    for better traceability and investigation capabilities.
    """

    # Creation audit
    created_by_email = Column(String(255), nullable=True, index=True)
    created_by_name = Column(String(255), nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False, index=True)

    # Update audit
    updated_by_email = Column(String(255), nullable=True, index=True)
    updated_by_name = Column(String(255), nullable=True)
    updated_at = Column(DateTime, onupdate=func.now(), server_default=func.now())

    # Deletion audit (soft delete support)
    deleted_by_email = Column(String(255), nullable=True, index=True)
    deleted_by_name = Column(String(255), nullable=True)
    deleted_at = Column(DateTime, nullable=True, index=True)

    def get_audit_info(self) -> Dict[str, Any]:
        """Get human-readable audit information for this record."""
        return {
            "created_by": {
                "email": self.created_by_email,
                "name": self.created_by_name,
                "timestamp": self.created_at.isoformat() if self.created_at else None
            },
            "updated_by": {
                "email": self.updated_by_email,
                "name": self.updated_by_name,
                "timestamp": self.updated_at.isoformat() if self.updated_at else None
            },
            "deleted_by": {
                "email": self.deleted_by_email,
                "name": self.deleted_by_name,
                "timestamp": self.deleted_at.isoformat() if self.deleted_at else None
            } if self.deleted_at else None
        }

    def set_created_by(self, user_email: str, user_name: str):
        """Set creation audit information."""
        self.created_by_email = user_email
        self.created_by_name = user_name

    def set_updated_by(self, user_email: str, user_name: str):
        """Set update audit information."""
        self.updated_by_email = user_email
        self.updated_by_name = user_name

    def set_deleted_by(self, user_email: str, user_name: str):
        """Set deletion audit information (soft delete)."""
        self.deleted_by_email = user_email
        self.deleted_by_name = user_name
        self.deleted_at = func.now()

    @property
    def is_deleted(self) -> bool:
        """Check if this record is soft deleted."""
        return self.deleted_at is not None


class AuditContext:
    """
    Helper class to capture and pass audit context information.
    Extracts human-readable info from User objects.
    """

    def __init__(self, user_email: str, user_name: str, user_id: Optional[str] = None):
        self.user_email = user_email
        self.user_name = user_name
        self.user_id = user_id  # Keep ID for reference if needed

    @classmethod
    def from_user(cls, user) -> "AuditContext":
        """Create audit context from User object."""
        if user is None:
            return cls("system", "System", None)

        # Handle both User objects and dict-like objects
        if hasattr(user, 'email'):
            return cls(
                user_email=user.email,
                user_name=getattr(user, 'name', user.email),
                user_id=getattr(user, 'id', None)
            )
        elif isinstance(user, dict):
            return cls(
                user_email=user.get('email', 'unknown'),
                user_name=user.get('name', user.get('email', 'unknown')),
                user_id=user.get('id')
            )
        else:
            # Fallback for string IDs
            return cls(f"user-{user}", f"User {user}", str(user))

    @classmethod
    def system(cls) -> "AuditContext":
        """Create system audit context for automated operations."""
        return cls("system", "System", "system")

    def __str__(self) -> str:
        return f"{self.user_name} ({self.user_email})"