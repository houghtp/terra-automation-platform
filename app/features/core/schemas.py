"""
Shared base schemas for common API patterns across all features.

These base classes provide standardized pagination, filtering, and response
patterns that can be inherited by feature-specific schemas.
"""
from typing import Any, Generic, List, TypeVar
from pydantic import BaseModel, Field


T = TypeVar('T')


class PaginatedRequest(BaseModel):
    """Base schema for paginated list requests with filtering."""

    limit: int = Field(default=50, ge=1, le=100, description="Maximum number of items to return")
    offset: int = Field(default=0, ge=0, description="Number of items to skip")

    class Config:
        """Pydantic config."""
        extra = "allow"  # Allow subclasses to add filter fields


class PaginatedResponse(BaseModel, Generic[T]):
    """Base schema for paginated list responses."""

    total: int = Field(..., description="Total number of items available")
    items: List[T] = Field(..., description="List of items in this page")
    limit: int = Field(..., description="Maximum items per page")
    offset: int = Field(..., description="Number of items skipped")
    has_more: bool = Field(..., description="Whether more items are available")

    @classmethod
    def create(cls, items: List[T], total: int, limit: int, offset: int) -> "PaginatedResponse[T]":
        """Helper method to create paginated response."""
        return cls(
            total=total,
            items=items,
            limit=limit,
            offset=offset,
            has_more=(offset + len(items)) < total
        )


class SortableRequest(PaginatedRequest):
    """Base schema for requests with sorting support."""

    sort_by: str = Field(default="created_at", description="Field to sort by")
    sort_order: str = Field(default="desc", description="Sort order (asc or desc)")


class SearchableRequest(PaginatedRequest):
    """Base schema for requests with search support."""

    search: str | None = Field(default=None, description="Search query string")


class StandardResponse(BaseModel):
    """Standard API response wrapper."""

    success: bool = Field(..., description="Whether the operation was successful")
    message: str = Field(..., description="Human-readable message")
    data: Any | None = Field(default=None, description="Response data")
    errors: List[str] | None = Field(default=None, description="List of error messages")


__all__ = [
    "PaginatedRequest",
    "PaginatedResponse",
    "SortableRequest",
    "SearchableRequest",
    "StandardResponse",
]
